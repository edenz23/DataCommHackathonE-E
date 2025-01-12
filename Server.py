from ServerMethods import *

# broadcast_port == the port that the server will send broadcast offers with.
# it needs to be known and the same for both the server and the client to initiate communication
BROADCAST_PORT = 13117

if __name__ == "__main__":
    # start a server instance
    server = ServerMethods(broadcast_port=BROADCAST_PORT)
    try:
        # on a separate thread, broadcast an offer message every second
        threading.Thread(target=server.broadcast_offer, args=(), daemon=True).start()

        # start TCP and UDP servers in separate threads
        threading.Thread(target=server.listen_for_TCP_requests, args=(), daemon=True).start()
        threading.Thread(target=server.listen_for_UDP_requests, args=(), daemon=True).start()

        input()  # stop server by pressing 'Enter'
    except KeyboardInterrupt:
        pass  # doesn't matter if the user stops the server with 'Enter' or Ctrl C
    finally:
        server.print_colored("Manual server shut down", "blue")
        server.get_server_stats()



