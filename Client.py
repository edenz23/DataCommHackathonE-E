import socket

#client_socket = server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # IPv4 and TCP
client_socket = server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4 and UDP

# leave HOSTNAME as empty string to accept connections from all addresses available and not just the same computer
HOSTNAME = ""
#HOSTNAME = socket.gethostbyname(socket.gethostname())  # ip address of localhost
port = 12345

#client_socket.connect((HOSTNAME, port))
#msg = client_socket.recv(1024)
#print(msg)

client_socket.sendto("msg to server".encode("utf-8"), (HOSTNAME, port))

#client_socket.close()
