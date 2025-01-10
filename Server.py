import socket
import struct
import threading
import time
import subprocess
import re
import platform


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


def broadcast_offer(broadcast_port, udp_port, tcp_port, interval=1):
    """
    Broadcasts an 'offer' message to clients.

    Parameters:
        broadcast_port: The well-known port for broadcasting the 'offer' message.
        udp_port: The port where the server will listen for UDP requests.
        tcp_port: The port where the server will listen for TCP requests.
        interval: Time interval between broadcasts (in seconds).
    """
    # Define the magic cookie and message type
    MAGIC_COOKIE = 0xabcddcba
    MESSAGE_TYPE = 0x2

    # Create a UDP socket for broadcasting
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Construct the offer packet
    packet = struct.pack('>IBHH', MAGIC_COOKIE, MESSAGE_TYPE, udp_port, tcp_port)

    try:
        broadcast_address = get_broadcast_address()
        print(f"Using broadcast address: {broadcast_address}")
        while True:
            # Broadcast the packet to the determined broadcast address
            udp_socket.sendto(packet, (broadcast_address, broadcast_port))
            print(f"Broadcasted offer on port {broadcast_port} "
                  f"(UDP port: {udp_port}, TCP port: {tcp_port})")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Broadcasting stopped.")
    finally:
        udp_socket.close()


def handle_tcp_client(client_socket, client_address):
    try:
        # Read file size from client
        file_size = int(client_socket.recv(1024).decode().strip())
        print(f"TCP request from {client_address}: {file_size} bytes")

        data = b'x' * file_size  # send the number of Bytes as received from the client
        client_socket.sendall(data)
        print(f"Finished TCP transfer to {client_address}")
    except Exception as e:
        print(f"Error with TCP client {client_address}: {e}")
    finally:
        client_socket.close()

def handle_udp_request(packet, client_address, udp_socket):
    try:
        # Decode the packet (assuming a simple protocol)
        MAGIC_COOKIE = 0xabcddcba
        MESSAGE_TYPE = 0x4
        REQUEST_PACKET_FORMAT = '>IBQ'  # Magic cookie (4 bytes), type (1 byte), file size (8 bytes)
        magic_cookie, message_type, file_size = struct.unpack(REQUEST_PACKET_FORMAT, packet)

        if magic_cookie != MAGIC_COOKIE:
            print(f"Invalid request packet from {client_address}")
            return

        print(f"UDP request from {client_address}: {file_size} bytes")

        # Simulate sending data in chunks
        # use global/class scope variable to get file size
        total_segments = file_size // 1024  # Example: 1KB segments
        for segment in range(total_segments):
            payload = struct.pack('>IBQQ', MAGIC_COOKIE, MESSAGE_TYPE, total_segments, segment) + b'x' * 1024
            udp_socket.sendto(payload, client_address)
        print(f"Finished UDP transfer to {client_address}")
    except Exception as e:
        print(f"Error with UDP client {client_address}: {e}")


def listen_for_TCP_requests(tcp_port):
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind(('', tcp_port))
    tcp_socket.listen(5)
    print(f"TCP server listening on port {tcp_port}")

    while True:
        client_socket, client_address = tcp_socket.accept()
        print(f"Accepted TCP connection from {client_address}")
        threading.Thread(target=handle_tcp_client, args=(client_socket, client_address)).start()


def listen_for_UDP_requests(udp_port_for_requests):
    udp_main_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_main_socket.bind(('', udp_port_for_requests))
    print(f"UDP server listening on port {udp_port_for_requests}")

    while True:
        request_packet, client_address = udp_main_socket.recvfrom(1024)
        print(f"Received UDP request from {client_address}")

        # Create a new UDP socket for the client
        udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_client_socket.bind(('', 0))  # Dynamically assign port
        udp_port = udp_client_socket.getsockname()[1]
        print(f"Assigned new UDP port {udp_port} for client {client_address}")
        threading.Thread(target=handle_udp_request, args=(request_packet, client_address, udp_client_socket)).start()


# Example usage
if __name__ == "__main__":
    # Well-known broadcast port, and server-specific UDP/TCP ports
    broadcast_port = 13117  # check if we know for sure that clients know in advance the port number for broadcast
    udp_port = 20245  # For receiving UDP speed test requests
    tcp_port = 30345  # For receiving TCP speed test requests

    threading.Thread(target=broadcast_offer, args=(broadcast_port, udp_port, tcp_port), daemon=True).start()


    # Start TCP and UDP servers in separate threads
    threading.Thread(target=listen_for_TCP_requests, args=(tcp_port,), daemon=True).start()
    #threading.Thread(target=udp_server, args=(udp_port,), daemon=True).start()

    input("press enter to close the main thread..\n")



