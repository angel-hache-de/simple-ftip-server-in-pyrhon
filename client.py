import socket
import time
from files import *
import os

DIVIDER = "<DIVIDER>"
HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server
BUFF_SIZE = 1024

class Client(EndDevice):
    def __init__(self, host, port, buffer_size):
      super().__init__(
        buffer_size=buffer_size, 
        port=port,
        host=host
      )

    def show_menu(self):
      while True:
        print("1. See local files")
        print("2. See remote files")
        print("3. Upload file(s)")
        print("4. Upload directory")
        print("5. Download file(s)")
        print("6. Download directory")
        print("7. Remove remote file(s)")
        print("8. Remove local file(s)")
        print("9. Remove remote directory")
        print("10. Remove local directory")
        print("11. Exit")

        opt = int(input("Enter your option:"))

        if opt in range(1, 12):
          break

      return opt

    def send_request(self):
      while True:
        opt = self.show_menu()
      
        if(opt == 11):
          break

        switch = {
          1: lambda :print(
              list_files_pretty(os.getcwd())
            ),
          2: lambda :self.get_remote_files(2),
          3: lambda :self.send_files(3),
          4: lambda :self.send_directory(4),
          5: lambda :self.receive_files(5),
          6: lambda :self.receive_dir(6),
          7: lambda :self.delete_remote_paths(opt=7, list_opt=10),
          8: lambda :self.delete_local_paths(list_opt=1),
          9: lambda :self.delete_remote_paths(opt=9, list_opt=11),
          10: lambda :self.delete_local_paths(list_opt=0),
        }

        function = switch.get(opt)
        function()

    def get_remote_files(self, opt):
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((self.host, self.port))

        s.sendall(f"{opt}".encode("utf-8"))

        files = s.recv(BUFF_SIZE).decode("utf-8")
        print(files)

    def send_files(self, opt):
      remote_dirs = self.get_remotes_paths(opt=11)
      remote_dir = self.choose_paths(just_one=True, paths=remote_dirs)

      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((self.host, self.port))

        s.sendall(f"{opt}".encode("utf-8"))
        files = list(get_files())
        super().send_files(s, files, remote_dir)

        print(s.recv(BUFFER_SIZE).decode("utf-8"))

    def send_directory(self, opt):
      remote_dirs = self.get_remotes_paths(opt=11)
      remote_dir = self.choose_paths(just_one=True, paths=remote_dirs)

      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((self.host, self.port))

        s.sendall(f"{opt}".encode("utf-8"))

        dir = get_directory()
        super().send_directory(socket=s, dir=dir, remote_dir=remote_dir)

        print(s.recv(BUFFER_SIZE).decode("utf-8"))

    def receive_files_list(self):
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((self.host, self.port))

        # Send the folder name
        data = s.recv(BUFFER_SIZE).decode("UTF-8")
        print(data)

    def get_remotes_paths(self, opt):
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((self.host, self.port))

        s.sendall(f"{opt}".encode("utf-8"))

        # Send the folder name
        data = s.recv(BUFFER_SIZE).decode("UTF-8")
        # items is a list of files or directories
        paths = json.loads(data)
        # Root dir
        paths.insert(0, "/")

      return paths

    # Receive files/directories with full path
    def choose_paths(self, paths, just_one=False):
        if just_one:
          print("Enter the # of your desired path.")
        else:
          print("Enter the # of your desired paths. (Eg. 1, 2, 3):")

        print("#  | Path")
        for i in range(len(paths)):
          print(f"{i}  {paths[i]}")

        #For multiple choose
        picked_options = input("Enter your option(s): ")
        # Parse the string "1, 2, 4, 5" to int
        picked_paths = [int(opt) for opt in picked_options.split(",")]
        #map(lambda str_number:int(str_number), picked_options.split(","))

        if not just_one:
          return [paths[i] for i in picked_paths]
        else:
          return paths[picked_paths[0]]

    def receive_files(self, opt):
      remote_files = self.get_remotes_paths(opt=10)
      files_to_download = self.choose_paths(paths=remote_files)

      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((self.host, self.port))

        s.sendall(f"{opt}".encode("utf-8"))
        time.sleep(0.5)
        s.sendall(json.dumps(files_to_download).encode("utf-8"))
        super().receive_files(s)

        print(s.recv(BUFFER_SIZE).decode("utf-8"))

    def receive_dir(self, opt):
      remote_dirs = self.get_remotes_paths(opt=11)
      remote_dir = self.choose_paths(just_one=True, paths=remote_dirs)

      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((self.host, self.port))

        s.sendall(f"{opt}".encode("utf-8"))
        time.sleep(0.5)
        s.sendall(json.dumps([remote_dir]).encode("utf-8"))
        # The remote dir has an initial "/" and is removed
        super().receive_dir(socket=s)

        print(s.recv(BUFFER_SIZE).decode("utf-8"))
        
    def delete_remote_paths(self, opt, list_opt):
      remote_paths = self.get_remotes_paths(opt=list_opt)
      paths_to_delete = self.choose_paths(paths=remote_paths)

      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((self.host, self.port))

        s.sendall(f"{opt}".encode("utf-8"))
        time.sleep(0.5)
        s.sendall(json.dumps(paths_to_delete).encode("utf-8"))

        print(s.recv(BUFFER_SIZE).decode("utf-8"))
        # The remote dir has an initial "/" and is removed
        #super().receive_dir(socket=s)

    def delete_local_paths(self, list_opt):
      paths = list(
        get_dirs_w_subpath(os.getcwd())
        if list_opt == 0 else
        get_files_w_subpath(os.getcwd())
      )

      paths_to_delete = self.choose_paths(paths=paths)
      for path in paths_to_delete:
        super().delete_path(
          remove_initial_slash(path)
        )
      print("Done")

try:
  client = Client(HOST, PORT, BUFF_SIZE)
  client.send_request()
except Exception as e:
  print("Something went wrong")
  print(e)
