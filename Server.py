import socket

# server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # IPv4 and TCP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4 and UDP


#print(socket.gethostname())
#print(socket.gethostbyname(socket.gethostname()))

# leave HOSTNAME as empty string to accept connections from all addresses available and not just the same computer
HOSTNAME = ""
#HOSTNAME = socket.gethostbyname(socket.gethostname())  # ip address of localhost
port = 12345

server_socket.bind((HOSTNAME, port))
#server_socket.listen() # for tcp

"""
while True:
    client_socket, client_address = server_socket.accept()
    print(f"Server is connected to {client_address}")

    client_socket.send(b"a random message for the client")

    server_socket.close()
    break
"""

msg, address = server_socket.recvfrom(1024)
print(msg.decode("utf-8"))
print(f"msg size in bytes: {len(msg)}")
print(address)

