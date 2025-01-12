import socket
import struct
import time
import re
import threading
import subprocess
import platform
from CustomExceptions import *


class ServerMethods:
    def __init__(self, magic_cookie=0xabcddcba, broadcast_port=13117, udp_speed_test_segment_size=1024):
        self.MAGIC_COOKIE = magic_cookie
        self.offer_msg_type = 0x2
        self.offer_packet_format = '>IBHH'  # Magic cookie (4 bytes), type (1 byte), ports (2 bytes each)
        self.request_msg_type = 0x3
        self.request_packet_format = '>IBQ'  # Magic cookie (4 bytes), type (1 byte), file size (8 bytes)
        self.payload_msg_type = 0x4
        self.payload_packet_format = '>IBQQ'  # Magic cookie (4 bytes), type (1 byte), total segments (8 bytes), current segment (8 bytes)
        self.broadcast_port = broadcast_port
        self.tcp_main_socket, self.tcp_main_port, self.udp_main_socket, self.udp_main_port = self.server_startup()
        self.udp_segment_size = udp_speed_test_segment_size
        # vars for server stats
        self.num_of_broadcast_offers_sent = 0
        self.num_of_tcp_speed_tests = 0
        self.clients_tcp_tests_list = set()
        self.num_of_udp_speed_tests = 0
        self.clients_udp_tests_list = set()
        self.overall_data_sent = 0


    @staticmethod
    def server_startup():
        """Create the 2 main sockets that will receive requests from clients, and bind them to a dynamic port"""
        tcp_main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_main_socket.bind(('', 0))  # Dynamically assign port
        tcp_main_port = tcp_main_socket.getsockname()[1]

        udp_main_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_main_socket.bind(('', 0))  # Dynamically assign port
        udp_main_port = udp_main_socket.getsockname()[1]
        return tcp_main_socket, tcp_main_port, udp_main_socket, udp_main_port

    @staticmethod
    def get_broadcast_address():
        """Determine the broadcast address dynamically for macOS/Linux and Windows."""
        try:
            if platform.system() in ["Linux", "Darwin"]:  # macOS and Linux
                # Run ifconfig to get network details
                result = subprocess.run(['ifconfig'], capture_output=True, text=True)
                output = result.stdout

                # Find the broadcast address using regex
                match = re.search(r'broadcast (\d+\.\d+\.\d+\.\d+)', output)
                if match:
                    return match.group(1)
                else:
                    raise RuntimeError("Broadcast address not found in network configuration.")

            elif platform.system() == "Windows":
                # Run ipconfig to get network details
                result = subprocess.run(['ipconfig'], capture_output=True, text=True)
                output = result.stdout

                # Use regex to extract IPv4 and subnet mask
                ipv4_match = re.search(r'IPv4 Address.*: (\d+\.\d+\.\d+\.\d+)', output)
                subnet_match = re.search(r'Subnet Mask.*: (\d+\.\d+\.\d+\.\d+)', output)

                if ipv4_match and subnet_match:
                    ipv4_address = ipv4_match.group(1)
                    subnet_mask = subnet_match.group(1)

                    # Calculate the broadcast address
                    ipv4_parts = list(map(int, ipv4_address.split('.')))
                    subnet_parts = list(map(int, subnet_mask.split('.')))
                    broadcast_parts = [(ipv4_parts[i] | ~subnet_parts[i] & 0xFF) for i in range(4)]
                    broadcast_address = '.'.join(map(str, broadcast_parts))
                    return broadcast_address
                else:
                    raise RuntimeError("Could not determine broadcast address from ipconfig output.")
            else:
                raise RuntimeError("Unsupported operating system.")

        except Exception as e:
            raise RuntimeError(f"Failed to determine broadcast address: {e}")

    def broadcast_offer(self, interval=1):
        """
        Broadcasts an 'offer' message to clients.

        Parameters:
            interval: Time interval between broadcasts (in seconds).
        """
        # Create a UDP socket for broadcasting
        udp_broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Construct the offer packet
        packet = struct.pack(self.offer_packet_format, self.MAGIC_COOKIE, self.offer_msg_type, self.udp_main_port, self.tcp_main_port)

        try:
            broadcast_address = self.get_broadcast_address()
            self.print_colored(f"Server started, listening on IP address {self.get_server_ip()}", "green")
            while True:
                # Broadcast the packet to the determined broadcast address
                udp_broadcast_socket.sendto(packet, (broadcast_address, self.broadcast_port))
                self.num_of_broadcast_offers_sent += 1
                time.sleep(interval)
        except KeyboardInterrupt:
            self.print_colored("Broadcasting stopped.", "red")
        finally:
            udp_broadcast_socket.close()

    def handle_tcp_client(self, client_socket, client_address):
        try:
            # Read file size from client
            file_size = int(client_socket.recv(1024).decode().strip())
            self.overall_data_sent += file_size  # add for server stats

            # Chunk size for sending data
            chunk_size = 1048576  # 1 MB

            # Generate and send data in chunks, will be easier on memory and CPU + supports files_size > 2GB
            total_sent = 0
            while total_sent < file_size:
                remaining = file_size - total_sent
                chunk_size_to_send = min(chunk_size, remaining)
                chunk = b'x' * chunk_size_to_send  # Generate chunk dynamically
                client_socket.sendall(chunk)
                total_sent += chunk_size_to_send

        except Exception as e:
            if e.__str__() == "[Errno 32] Broken pipe":
                self.print_colored(f"TCP client {client_address} cut the connection to the server", "red")
            else:
                self.print_colored(f"Error with TCP client {client_address}: {e}", "red")
        finally:
            client_socket.close()

    def handle_udp_request(self, file_size, client_address, udp_socket):
        try:
            # check if the requested file size fits in a segment size window,
            # if not, add another segment for the trailing data
            if file_size % self.udp_segment_size == 0:
                total_segments = file_size // self.udp_segment_size
            else:
                total_segments = file_size // self.udp_segment_size + 1
            segment = 0
            while segment < total_segments:
                payload = struct.pack(self.payload_packet_format, self.MAGIC_COOKIE, self.payload_msg_type, total_segments, segment) + b'x' * self.udp_segment_size
                udp_socket.sendto(payload, client_address)
                segment += 1
        except Exception as e:
            self.print_colored(f"Error with UDP client {client_address}: {e}", "red")
        finally:
            udp_socket.close()

    def listen_for_TCP_requests(self):
        """A function that runs concurrent threads for each speed-test connection over TCP"""
        self.tcp_main_socket.listen()
        while True:
            try:
                client_socket, client_address = self.tcp_main_socket.accept()  # blocking function, not busy-wait
                self.num_of_tcp_speed_tests += 1  # add for server stats
                self.clients_tcp_tests_list.add(client_address[0])  # add for server stats
                threading.Thread(target=self.handle_tcp_client, args=(client_socket, client_address)).start()
            except Exception as e:
                self.print_colored(e, "red")

    def listen_for_UDP_requests(self):
        """A function that runs concurrent threads for each speed-test connection over UDP"""
        while True:
            try:
                request_packet, client_address = self.udp_main_socket.recvfrom(1024)  # blocking function, not busy-wait
                magic_cookie, message_type, file_size = struct.unpack(self.request_packet_format, request_packet)
                if magic_cookie != self.MAGIC_COOKIE or message_type != self.request_msg_type:
                    raise InvalidRequestFormat(f"Invalid request from {client_address}")

                # Create a new UDP socket for the client
                udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                udp_client_socket.bind(('', 0))  # Dynamically assign port

                self.num_of_udp_speed_tests += 1  # add for server stats
                self.clients_udp_tests_list.add(client_address[0])  # add for server stats
                self.overall_data_sent += file_size  # add for server stats

                threading.Thread(target=self.handle_udp_request, args=(file_size, client_address, udp_client_socket)).start()
            except Exception as e:
                self.print_colored(e, "red")

    def get_server_stats(self):
        """A function to print some stats about the server after the user manually closes it"""
        self.print_colored("Server Statistics and information:", "background green")
        print(f"Number of broadcast offer sent while running: {self.num_of_broadcast_offers_sent}")
        print(f"Number of Speed Tests: {self.num_of_tcp_speed_tests+self.num_of_udp_speed_tests}")
        print(f"Number of TCP Speed Tests: {self.num_of_tcp_speed_tests}")
        print(f"Number of UDP Speed Tests: {self.num_of_udp_speed_tests}")
        if len(self.clients_tcp_tests_list) != 0:
            print(f"Unique clients that ran TCP speed tests: {self.clients_tcp_tests_list}")
        if len(self.clients_udp_tests_list) != 0:
            print(f"Unique clients that ran UDP speed tests: {self.clients_udp_tests_list}")
        formatted_data_sent = self.overall_data_sent
        unit = "Bytes"
        if formatted_data_sent >= 1073741824:  # 1GB
            formatted_data_sent /= 1073741824
            unit = "GB"
        elif formatted_data_sent >= 1048576:  # 1MB
            formatted_data_sent /= 1048576
            unit = "MB"
        elif formatted_data_sent >= 1024:  # 1KB
            formatted_data_sent /= 1024
            unit = "KB"
        print(f"Overall sent data: {round(formatted_data_sent, 1)} {unit}")

    @staticmethod
    def get_server_ip():
        """A function to get the current server ip (and to avoid returning 127.0.0.1 localhost)"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Connect to a non-routable external address
                s.connect(("8.8.8.8", 80))
                server_ip = s.getsockname()[0]
            return server_ip
        except Exception as e:
            return socket.gethostbyname(socket.gethostname())

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
                "magenta": "\u001b[35m",
                "background green": "\u001b[42m"
            }
            if color not in colors_dict.keys():
                raise UnsupportedColor()
            if limit_index == -1:
                print(f"{colors_dict[color]}{msg}\u001b[0m")
            else:
                print(f"{colors_dict[color]}{msg[:limit_index]}\u001b[0m{msg[limit_index:]}")
        except UnsupportedColor:
            print(msg)

