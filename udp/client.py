from socket import *
import time

def ping(host, port):
    resps = []
    # Create a UDP socket
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    # Set socket timeout as 1 second
    clientSocket.settimeout(1)
    
    # Ping for 10 times
    try:
        for seq in range(1,11):
            # Create the ping message
            send_time = time.time()
            # Example message: Ping 3 1696804876.324
            message = 'Ping {0} {1}\n'.format(seq, send_time)

            try:
                # Send the UDP packet with Ping message to the server
                clientSocket.sendto(message.encode(), (host, port))

                # Wait for the server response
                start_recv = time.time();
                response, address = clientSocket.recvfrom(1024)
                end_recv = time.time();
            
                # Calculate the RTT
                rtt = (end_recv - start_recv)

                # Record Server response
                response = response.decode().strip()
                resps.append((seq, response, rtt))

            except timeout:
                # Server does not respond within 1 second
                resps.append((seq, 'Request timed out', 0))
            
            except Exception as e:
                # Handle other exceptions
                resps.append((seq, str(e), 0))
    
    finally:
        clientSocket.close()

    return resps

if __name__ == '__main__':
    resps = ping('localhost', 12000)
    print(resps)