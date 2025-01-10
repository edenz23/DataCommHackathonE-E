import socket
import struct
import threading
import time
import re
from CustomExceptions import *


class ClientMethods:
    def __init__(self, magic_cookie=0xabcddcba):
        self.MAGIC_COOKIE = magic_cookie
        self.file_size, self.num_of_tcp_conn, self.num_of_udp_conn = self.client_startup()
        self.tcp_request_port = None  # the tcp port received in the 'offer' message from the server
        self.udp_request_port = None  # the udp port received in the 'offer' message from the server
        self.server_ip = None

    def client_startup(self):
        unit_multiplier_dict = {"": 1, "Bytes": 1, "KB": 1024, "MB": 1048576, "GB": 1073741824}
        while True:  # loop until the user provides acceptable values for speed test
            try:
                # 1) get file size for speed test
                self.print_colored("-"*40, "blue")
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
                file_size = round(
                    file_size_number * unit_multiplier_dict[file_size_units])  # determine final file size to get

                # 2) get number of TCP connections
                num_of_tcp_conn_usr_input = input("Insert the number of TCP connections you want to have: ")
                tcp_rgx = re.findall(r"^\d+$", num_of_tcp_conn_usr_input)
                if len(tcp_rgx) == 0:
                    raise InvalidClientInput("Not a valid input for 'number of TCP connections'")
                num_of_tcp_conn = int(tcp_rgx[0])

                # 3) get number of UDP connections
                num_of_udp_conn_usr_input = input("Insert the number of UDP connections you want to have: ")
                udp_rgx = re.findall(r"^\d+$", num_of_udp_conn_usr_input)
                if len(udp_rgx) == 0:
                    raise InvalidClientInput("Not a valid input for 'number of UDP connections'")
                num_of_udp_conn = int(udp_rgx[0])

                break  # if everything was OK until this part, we can break the while loop
            except Exception as err:
                self.print_colored(err, "red")
        return file_size, num_of_tcp_conn, num_of_udp_conn

    def listen_for_offers(self, broadcast_port):
        """
        Listens for broadcasted 'offer' messages from servers.

        Parameters:
            broadcast_port: The well-known port to listen on for broadcasts.
        """
        MESSAGE_TYPE = 0x2  # 'offer' message type
        OFFER_PACKET_FORMAT = '>IBHH'  # Packet format: cookie (4 bytes), type (1 byte), ports (2 bytes each)

        # Create a UDP socket
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # set socket over UDP with IPv4
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)  # option to allow IP wildcard values to work in the network
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)  # option to allow socket the receive broadcast messages
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT,1)  # option to allow multiple clients on the same host

        # Bind to the broadcast port to listen for offers
        udp_socket.bind(('', broadcast_port))
        self.print_colored("Client started, listening for offer requests...", "cyan")

        try:
            while True:
                # Receive a broadcast packet
                packet, server_address = udp_socket.recvfrom(1024)

                # Parse the packet
                magic_cookie, message_type, udp_port, tcp_port = struct.unpack(OFFER_PACKET_FORMAT, packet)

                # Validate the magic cookie and message type
                if magic_cookie == self.MAGIC_COOKIE and message_type == MESSAGE_TYPE:
                    self.print_colored(f"Received offer from {server_address[0]}:", "cyan")
                    #print(f"  Server UDP Port: {udp_port}")
                    #print(f"  Server TCP Port: {tcp_port}")

                    # successfully got an 'offer' message. stop listening and run speed test to the offering server
                    self.tcp_request_port = tcp_port
                    self.udp_request_port = udp_port
                    self.server_ip = server_address[0]
                    break
                else:
                    self.print_colored("Invalid offer packet received", "red")
        except struct.error:
            self.print_colored("Invalid packet received", "red")
        except KeyboardInterrupt:
            self.print_colored("Stopped listening for offers", "red")
        finally:
            udp_socket.close()

    def run_tcp_test(self, transfer_id):
        """
        Establishes a single TCP connection to the server and sends a message.

        Parameters:
            transfer_id: An identifier for the client connection
        """
        try:
            # Create a socket for the connection
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((self.server_ip, self.tcp_request_port))

                # Send the file size to get from the server
                client_socket.sendall(f"{self.file_size}\n".encode('utf-8'))

                # Receive the response
                start_time = time.time()
                while True:  # receive the data in chunks of 1024 Bytes, and support dynamic file sizes
                    response = client_socket.recv(1024)
                    if not response:
                        break  # connection closed
                total_time = time.time() - start_time  # measure the time it took for the whole file size
                print(f"TCP transfer #{transfer_id} finished, total time: {round(total_time, 5)} seconds, total speed: {round(self.file_size/total_time*8, 3)} bits/second")
        except Exception as e:
            print(f"\u001b[31mTCP Transfer {transfer_id}: Error: {e}\u001b[0m")

    @staticmethod
    def print_colored(msg, color):
        colors_dict = {
            "green": "\u001b[32m",
            "red": "\u001b[31m",
            "blue": "\u001b[34m",
            "cyan": "\u001b[36m"
        }
        print(f"{colors_dict[color]}{msg}\u001b[0m")

