import socket
import struct
import threading
import time
import re
from CustomExceptions import *


def listen_for_offers(broadcast_port):
    """
    Listens for broadcasted 'offer' messages from servers.

    Parameters:
        broadcast_port: The well-known port to listen on for broadcasts.
    """
    # Define the expected magic cookie and message type
    MAGIC_COOKIE = 0xabcddcba
    MESSAGE_TYPE = 0x2  # 'offer' message type
    OFFER_PACKET_FORMAT = '>IBHH'  # Packet format: cookie (4 bytes), type (1 byte), ports (2 bytes each)

    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # set socket over UDP with IPv4
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # option to allow IP wildcard values to work in the network
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # option to allow socket the receive broadcast messages
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # option to allow multiple clients on the same host

    # Bind to the broadcast port to listen for offers
    udp_socket.bind(('', broadcast_port))
    print(f"Listening for broadcasting offers on UDP port {broadcast_port}...")

    try:
        while True:
            # Receive a packet
            packet, address = udp_socket.recvfrom(1024)  # 1024 is the buffer size
            print(f"Received packet from {address}")

            try:
                # Parse the packet
                magic_cookie, message_type, udp_port, tcp_port = struct.unpack(OFFER_PACKET_FORMAT, packet)

                # Validate the magic cookie and message type
                if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE:
                    print(f"Offer received from {address[0]}:")
                    print(f"  Server UDP Port: {udp_port}")
                    print(f"  Server TCP Port: {tcp_port}")
                    # successfully got an 'offer' message. stop listening and run speed test to the offering server
                    break
                else:
                    print("Invalid offer packet received.")
            except struct.error:
                print("Malformed packet received.")
    except KeyboardInterrupt:
        print("Stopped listening for offers.")
    finally:
        udp_socket.close()


def client_startup():
    unit_multiplier_dict = {"": 1, "Bytes": 1, "KB": 1024, "MB": 1048576, "GB": 1073741824}
    while True:  # loop until the user provides acceptable values for speed test
        try:
            # 1) get file size for speed test
            print("-"*40)
            file_size_usr_input = input("Insert file size for speed test (format: NUMBER UNIT) ex '5 MB', default UNIT == Bytes: ")
            input_rgx = re.findall(r"(\d+\.\d+)\s?(\w+)?|(\d+)\s?(\w+)?", file_size_usr_input)
            if len(input_rgx) == 0:
                raise InvalidClientInput()
            if input_rgx[0][0] != "":  # it means the user has given a float number input
                file_size_number = float(input_rgx[0][0])
                file_size_units = input_rgx[0][1]
            else:  # it means the user has given an int number input
                file_size_number = int(input_rgx[0][2])
                file_size_units = input_rgx[0][3]
            if file_size_units not in unit_multiplier_dict.keys() and file_size_units != '':  # check if the user has given a valid UNIT size
                raise InvalidClientInput(f"Units provided '{file_size_units}' arent supported for this speed test")
            file_size = round(file_size_number * unit_multiplier_dict[file_size_units])  # determine final file size to get

            # 2) get number of TCP connections
            num_of_tcp_conn_usr_input = input("Insert the number of TCP connections you want to have: ")
            tcp_rgx = re.findall(r"^\d+$", num_of_tcp_conn_usr_input)
            if len(tcp_rgx) == 0:
                raise InvalidClientInput("Not a valid input for 'number of TCP connections'")
            num_of_tcp_conn = tcp_rgx[0]

            # 3) get number of UDP connections
            num_of_udp_conn_usr_input = input("Insert the number of UDP connections you want to have: ")
            udp_rgx = re.findall(r"^\d+$", num_of_udp_conn_usr_input)
            if len(udp_rgx) == 0:
                raise InvalidClientInput("Not a valid input for 'number of UDP connections'")
            num_of_udp_conn = udp_rgx[0]

            break  # if everything was OK until this part, we can break the while loop
        except Exception as err:
            print(err)
    return file_size, num_of_tcp_conn, num_of_udp_conn


# Example usage
if __name__ == "__main__":
    """
    Main of client will be comprised of several stages:
    1) ask the user's input about number and type of speed test connections + file size for test.
    2) continuously look for 'offer' messages from broadcasting servers.
    3) after receiving an 'offer' message, AND verifying that the message is valid (magic-cookie, valid message type),
       determine what to do for each connection type:
            a) for TCP, use the TCP port in the 'offer' message to establish connection and run the speed test
            b) for UDP, send a request and let the server deal with that
    4) measure stats about each connection
    """

    file_size, tcp_conn_num, udp_conn_num = client_startup()  # 1

    broadcast_port = 13117
    listen_for_offers(broadcast_port)  # 2






"""
import socket
import struct
import threading
import time

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
"""