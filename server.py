import socket
from files import *
import time
import json

# This is my path
current_path = os.getcwd()

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
BUFF_SIZE = 1024
DIVIDER = "<DIVIDER>"  

class Server(EndDevice):
  def __init__(self):
    super().__init__(buffer_size=0, port=0, host="")
    self.s_connection = None

  def config(self, port, host, buffer_size):
    self.port = port
    self.host = host
    self.buffer_size = buffer_size

  def disconnect(self):
    # close the server socket
    self.s_connection.close()


  def listen(self):
    try:
      self.s_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.s_connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

      self.s_connection.bind((self.host, self.port))

      self.s_connection.listen()

      print("Server listening")
      while True:
        self.handle_reqs()

    except Exception as e:
      print("Disconnecting server...")
      self.disconnect()
      print(e)

  def handle_reqs(self):
    client, addr = self.s_connection.accept()
    print(f"{addr} is connected")

    opt = client.recv(BUFF_SIZE).decode("utf-8")
    opt = int(opt)    
    print(f"Received opt: {opt}")
    if opt not in range(0, 13):
      return

    switch = {
      2: lambda :self.send_files_list(client),
      3: lambda :self.receive_files(client),
      4: lambda :self.receive_dir(client),
      5: lambda :self.send_files(client),
      6: lambda :self.send_directory(client),
      7: lambda :self.delete_path(client),
      9: lambda :self.delete_path(client),
      10: lambda :self.send_files_with_path(client),
      11: lambda :self.send_dirs_with_path(client),
    }

    function = switch.get(opt)
    function()
    time.sleep(0.5)
    client.sendall("Done".encode("utf-8"))
    client.close()

  def send_files_list(self, client):
    #self.show_menu()
    client.sendall(list_files_pretty(
      current_path, 0
    ).encode("utf-8"))

  def send_files_with_path(self, client):
    files = list(get_files_w_subpath(current_path))
    client.sendall(json.dumps(files).encode("utf-8"))

  def send_dirs_with_path(self, client):
    dirs = list(get_dirs_w_subpath(current_path))
    client.sendall(json.dumps(dirs).encode("utf-8"))

  def receive_paths_list(self, client, include_size=False):
    data = client.recv(BUFFER_SIZE).decode("utf-8")
    paths_list = json.loads(data)

    paths = []
    for path in paths_list:
      new_path = os.path.join(current_path, path[1:])
      # Si se ha recibido un path con "/" de mas
      if current_path not in new_path or not os.path.exists(new_path):
        continue

      if include_size:
        paths.append((new_path, os.path.getsize(new_path)))
      else:
        paths.append(new_path)

    return paths

  # OVERWRITE METHODS
  def send_files(self, client):
    files = self.receive_paths_list(client)

    super().send_files(client, files, "")

  def send_directory(self, client):
    dirs = self.receive_paths_list(client)
    super().send_directory(client, dirs[0])

  def delete_path(self, client):
    paths = client.recv(BUFFER_SIZE).decode("utf-8")
    # List of paths
    paths = json.loads(paths)

    for path in paths:
      super().delete_path(
        remove_initial_slash(path)
      )

server = Server()
server.config(PORT, HOST, BUFF_SIZE)
server.listen()
server.disconnect()
