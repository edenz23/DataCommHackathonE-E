from ClientMethods import *


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
    client = ClientMethods()  # init the client and run startup procedure

    broadcast_port = 13117  # must be set on both the client AND the server
    client.listen_for_offers(broadcast_port)  # 2

    # start threads for each requested connection
    threads = []
    for i in range(client.num_of_tcp_conn):
        thread = threading.Thread(target=client.run_tcp_test, args=(i+1,), daemon=True)
        threads.append(thread)
        thread.start()
        #time.sleep(1)  # for testing

    #for i in range(client.num_of_udp_conn):
    #    thread = threading.Thread(target=client.run_udp_test, args=(i+1, ), daemon=True)
    #    threads.append(thread)
    #    thread.start()

    # after all transfers are complete, print a concluding message
    for thread in threads:
        thread.join()

    client.print_colored("All transfers complete, listening to offer requests", "green")

    input()

