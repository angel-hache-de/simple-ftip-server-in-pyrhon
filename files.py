# import OS module
from genericpath import isfile
import os
import shutil
import time
import json
from zipfile import ZipFile

from tkinter import Tk
from tkinter.filedialog import askdirectory, askopenfilenames

DIVIDER = "<DIVIDER>"
BUFFER_SIZE = 1024

# Similar to os.path.basename, in this case basename
# is the cwd
def remove_base_dir(path):
    return path[len(os.path.abspath("")):]

def remove_initial_slash(path):
  new_path = path
  while len(new_path) > 0 and new_path[0] == "/":
    if(len(new_path) == 1):
      new_path = ""
    else:
      new_path = new_path[1:]

  return new_path

# Get ALL the files inside a path, this include files inside
# folders
def get_files_w_subpath(path):
    for (root, dirs, files) in os.walk(path):
      for file in files:
        yield remove_base_dir(os.path.join(root, file))

# Get ALL the subdirectories inside a path, this include subdirectories 
# inside folders
def get_dirs_w_subpath(path):
    for (root, dirs, files) in os.walk(path):
      for dir in dirs:
        yield remove_base_dir(os.path.join(root, dir))

#Get the file tree as a string to send just one string
#on the socket
#Prints the tree with tabs on a more readable way
def list_files_pretty(path, number_spaces=0):
    files = ""
    dirs = []
    for file in os.listdir(path):
        if not os.path.isfile(os.path.join(path, file)):
            dirs.append(file)
        else:
            files += "".join(" " * number_spaces) + "[-]"
            files += f"{file}\n"

    for d in dirs:
        files += "".join(" " * number_spaces) + f"[+]{d}\n"
        files += list_files_pretty(os.path.join(path, d), number_spaces + 2)

    return files

# Return both file and size
def get_files():
    Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
    files = askopenfilenames() # show an "Open" dialog box and return the path to the selected file
    return get_files_size(files)

def get_files_size(files):
  for file in files:
    yield (file, os.path.getsize(file))

def get_directory():
    Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
    return askdirectory() # show an "Open" dialog box and return the path to the se

# Delete permanently files/directories
def delete_anything(path):  
  if os.path.exists(path):
    if os.path.isdir(path):
      shutil.rmtree(path)
    elif os.path.isfile(path):
      os.remove(path)

def zip_folder(filename, directory):
    #filename = "compressed"
    format = "zip"
    #directory = os.getcwd()
    shutil.make_archive(filename, format, directory)
    return os.path.getsize(f"./{filename}.zip")

def unzip_folder(file, path):
    with ZipFile(file, 'r') as zObject:
        # Extracting all the members of the zip 
        # into a specific location.
        zObject.extractall(path)

class EndDevice:
  def __init__(self, port, host, buffer_size):
    self.port = port
    self.host = host
    self.buffer_size = buffer_size

  def receive_files(self, socket, number=None, dir=None):
    number_and_dir = socket.recv(BUFFER_SIZE).decode("utf-8")
    number_and_dir = json.loads(number_and_dir)
    number_files = number_and_dir.get("number_files")
    cleaned_dir = remove_initial_slash(number_and_dir.get("dir"))
    destination_folder = os.path.join(os.path.curdir, cleaned_dir)

    for i in range(number_files):
      received = socket.recv(BUFFER_SIZE).decode("utf-8")
      filename, filesize = received.split(DIVIDER)

      # remove absolute path if there is
      filename = os.path.basename(filename)
      # convert to integer
      filesize = int(filesize)

      print(f"receiving: {filename}")
      with open(os.path.join(destination_folder, filename), "wb") as f:
        received = 0
        while received < filesize:
          # read 1024 bytes from the socket (receive)
          bytes_read = socket.recv(BUFFER_SIZE)

          # write to the file the bytes we just received
          f.write(bytes_read)
          # update the progress bar
          received += len(bytes_read)

          #time.sleep(2.0)
          print(f"Receiving: {str(int(received*100/filesize))}%", end="\r")


      print("")

  #Directories come as zip
  def receive_dir(self, socket):
    folder = socket.recv(BUFFER_SIZE).decode("utf-8")
    folder = os.path.join(
      os.path.curdir, 
      remove_initial_slash(folder)
    )

    #Create the directory where unzip de files
    if not os.path.exists(folder):
      os.mkdir(folder)

    #print("folder " + folder)
    EndDevice.receive_files(
      self=self,
      socket=socket,
      number=1,
      dir=folder
    )

    unzip_folder(os.path.join(folder, "zip.zip"), folder)
    os.remove(os.path.join(folder, "zip.zip"))

  # Files is none when called by Client
  # @param files list of tuple with the file name and size.
  def send_files(self, socket, files, dir=""):
    number_and_dir = {"number_files": len(files), "dir": dir}
    #Send the amount of files that will be send
    socket.sendall(bytes(json.dumps(number_and_dir), encoding="utf-8"))

    for file, size in files:
      print(f"Preparing to send: {os.path.basename(file)} / {size}B")
      socket.sendall(f"{file}{DIVIDER}{size}".encode("utf-8"))
      time.sleep(0.1)
      with open(file, "rb") as f:
          bytes_sent = 0
          while True:
              # read the bytes from the file
              bytes_read = f.read(BUFFER_SIZE)
              if not bytes_read:
                  # file transmitting is done
                  break
              # we use sendall to assure transimission in 
              # busy networks
              socket.sendall(bytes_read)
              bytes_sent += len(bytes_read)
              # update the progress bar and "flush"
              #time.sleep(0.5)
              print(f"Sending: {str(int(bytes_sent*100/size))}%", end="\r")
      print("")
      time.sleep(0.1)

  def send_directory(self, socket, dir, remote_dir=""):
    basename = os.path.basename(dir)
    remote_dir += "/" + basename
    # Send the folder name
    socket.sendall(f"{remote_dir}".encode("utf-8"))
    #print("dir" + dir)
    zip_size = zip_folder("zip", dir) #generates zip.zip
    EndDevice.send_files(
      self=self,
      socket=socket, 
      files=[("./zip.zip", zip_size)], 
      dir=remote_dir)
    #send_files_through_socket(socket, [("./zip.zip", zip_size)], False)
    os.remove("./zip.zip")

  def delete_path(self, path):
    path_to_delete = os.path.join(os.getcwd(), path)
    if os.getcwd() not in path_to_delete or not os.path.exists(path_to_delete):
      return
    print(path_to_delete)
    delete_anything(path_to_delete)

