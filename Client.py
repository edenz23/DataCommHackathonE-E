from ClientMethods import *
import threading

# broadcast_port == the port that the server will send broadcast offers with.
# it needs to be known and the same for both the server and the client to initiate communication
BROADCAST_PORT = 13117


def client_loop(client):
    """The client's Main code, set in a loop, so it'll only be stopped manually"""
    while True:
        # list for server's broadcast offer messages
        client.listen_for_offers()

        # start threads for each requested connection
        threads = []
        for i in range(client.num_of_udp_conn):
            thread = threading.Thread(target=client.run_udp_test, args=(i + 1,), daemon=True)
            threads.append(thread)
            thread.start()

        for i in range(client.num_of_tcp_conn):
            thread = threading.Thread(target=client.run_tcp_test, args=(i + 1,), daemon=True)
            threads.append(thread)
            thread.start()

        # after all transfers are complete, print a concluding message
        for thread in threads:
            thread.join()

        client.print_colored("All transfers complete, listening to offer requests", "green")
        client.print_colored("-" * 40, "blue")


if __name__ == "__main__":
    clnt = ClientMethods(broadcast_port=BROADCAST_PORT)  # init the client and run startup procedure
    try:
        # Run the client Main in a thread, so if the main thread receives a user input to stop, it'll stop the client's loop
        threading.Thread(target=client_loop, args=(clnt,), daemon=True).start()

        input()  # stop client by pressing 'Enter'
    except KeyboardInterrupt:
        pass  # doesn't matter if the user stops the client with 'Enter' or Ctrl C

