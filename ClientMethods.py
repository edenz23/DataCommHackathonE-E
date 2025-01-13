import socket
import struct
import time
import re
from CustomExceptions import *


class ClientMethods:
    def __init__(self, magic_cookie=0xabcddcba, broadcast_port=13117):
        self.MAGIC_COOKIE = magic_cookie
        self.file_size, self.num_of_tcp_conn, self.num_of_udp_conn = self.client_startup()
        self.tcp_request_port = None  # the tcp port received in the 'offer' message from the server
        self.udp_request_port = None  # the udp port received in the 'offer' message from the server
        self.server_ip = None
        self.offer_msg_type = 0x2
        self.offer_packet_format = '>IBHH'  # Magic cookie (4 bytes), type (1 byte), ports (2 bytes each)
        self.request_msg_type = 0x3
        self.request_packet_format = '>IBQ'  # Magic cookie (4 bytes), type (1 byte), file size (8 bytes)
        self.payload_msg_type = 0x4
        self.payload_packet_format = '>IBQQ'  # Magic cookie (4 bytes), type (1 byte), total segments (8 bytes), current segment (8 bytes)
        self.broadcast_port = broadcast_port

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

    def listen_for_offers(self):
        """Listens for broadcasted 'offer' messages from servers."""
        # Create a UDP socket
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # set socket over UDP with IPv4
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)  # option to allow IP wildcard values to work in the network
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST,1)  # option to allow socket the receive broadcast messages
        try:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT,1)  # option to allow multiple clients on the same host
        except Exception:
            pass # Doesnt work in Windows
        # Bind to the broadcast port to listen for offers
        udp_socket.bind(('', self.broadcast_port))
        self.print_colored("Client started, listening for offer requests...", "cyan")

        try:
            while True:
                # Receive a broadcast packet
                packet, server_address = udp_socket.recvfrom(1024)  # blocking function, not busy-wait

                # Parse the packet
                magic_cookie, message_type, udp_port, tcp_port = struct.unpack(self.offer_packet_format, packet)

                # Validate the magic cookie and message type
                if magic_cookie == self.MAGIC_COOKIE and message_type == self.offer_msg_type:
                    self.print_colored(f"Received offer from {server_address[0]}:", "cyan")
                    # successfully got an 'offer' message. stop listening and run speed test to the offering server
                    self.tcp_request_port = tcp_port
                    self.udp_request_port = udp_port
                    self.server_ip = server_address[0]
                    break
                else:
                    raise InvalidOfferFormat()
        except struct.error:
            raise InvalidOfferFormat()
        except KeyboardInterrupt:
            self.print_colored("Stopped listening for offers", "red")
        except Exception as e:
            self.print_colored(e, "red")
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
                    response = client_socket.recv(1024)  # blocking function, not busy-wait
                    if not response:
                        break  # connection closed
                total_time = time.time() - start_time  # measure the time it took for the whole file size
                prt = f"TCP transfer #{transfer_id} finished, total time: {round(total_time, 5)} seconds, total speed: {round(self.file_size/total_time*8, 3)} bits/second"
                self.print_colored(prt, "magenta", 23+len(str(transfer_id)))
        except Exception as e:
            self.print_colored(f"TCP Transfer {transfer_id}: Error: {e}", "red")


    def run_udp_test(self, transfer_id):
        """
        Establishes a single UDP connection to the server and sends a message.

        Parameters:
            transfer_id: An identifier for the client connection
        """
        try:
            # Create a socket for the connection
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Send the file size to the server and get new dynamic port to run speed test with
            request_message = struct.pack(self.request_packet_format, self.MAGIC_COOKIE, self.request_msg_type, self.file_size)
            client_socket.sendto(request_message, (self.server_ip, self.udp_request_port))

            segments_reached = 0
            start_time = time.time()
            client_socket.settimeout(1)  # stop receiving if no data has been reached for 1 second
            try:
                while True:  # keep receiving until the socket has a 1-second timeout
                    # 1024+21 makes sure that the speed test packets sent 1KB of data each, compensation for the header
                    data, server_address = client_socket.recvfrom(1024+21)  # blocking function, not busy-wait
                    # read the header which is the first 21 Bytes, can ignore the actual data sent
                    magic_cookie, message_type, total_segment_count, current_segment_count = struct.unpack(self.payload_packet_format, data[:21])
                    if magic_cookie == self.MAGIC_COOKIE and message_type == self.payload_msg_type:
                        segments_reached += 1
            except socket.timeout:
                total_time = time.time() - start_time - 1  # -1 to compensate for the 1 sec timeout of the socket
                prt = f"UDP transfer #{transfer_id} finished, total time: {round(total_time, 5)} seconds, total speed: {round(self.file_size/total_time*8, 3)} bits/second, percentage of packets received successfully: {round(segments_reached/total_segment_count*100, 2)}%”."
                self.print_colored(prt, "blue", 23+len(str(transfer_id)))
        except Exception as e:
            if e.__str__() == "cannot access local variable 'total_segment_count' where it is not associated with a value":
                self.print_colored(f"UDP Transfer {transfer_id}: No data received over the connection")
            else:
                self.print_colored(f"UDP Transfer {transfer_id}: Error: {e}", "red")

    @staticmethod
    def print_colored(msg, color, limit_index=-1):
        """
        prints message (or part of message) with colors

        Parameters:
            msg: The message to print
            color: the color the use, passed as a color 'name'
            limit_index: limit the number of chars to color from the start of the message. Optional
        """
        try:
            colors_dict = {
                "green": "\u001b[32m",
                "red": "\u001b[31m",
                "blue": "\u001b[34m",
                "cyan": "\u001b[36m",
                "magenta": "\u001b[35m"
            }
            if color not in colors_dict.keys():
                raise UnsupportedColor()
            if limit_index == -1:
                print(f"{colors_dict[color]}{msg}\u001b[0m")
            else:
                print(f"{colors_dict[color]}{msg[:limit_index]}\u001b[0m{msg[limit_index:]}")
        except UnsupportedColor:
            print(msg)

