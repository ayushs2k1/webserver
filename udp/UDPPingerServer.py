# We will need the following module to generate randomized lost packets
import random
from socket import *
import time
import hashlib
import sys

def serve(port):
    # Create a UDP socket
    # Notice the use of SOCK_DGRAM for UDP packets
    serverSocket = socket(AF_INET, SOCK_DGRAM)
    # Assign IP address and port number to socket
    serverSocket.bind(('', port))
    while True:
        try:
            # Generate random number in the range of 0 to 10
            rand = random.randint(0, 10)
            # Receive the client packet along with the address it is coming from
            message, address = serverSocket.recvfrom(1024)
            # Capture the time since epoch (in seconds) when the message is received. 
            # This will be later sent back to the client as the server timestamp
            s_time = time.time()
            # If rand is less is than 4, we consider the packet lost and do not respond
            if rand < 4:
                continue
            
            # Otherwise, the server responds
            # Example client message: "Ping 3 1696804876.324" → ['Ping', '3', '1696804876.324']
            m = message.decode().split()
            seq = m[1]
            c_time = m[2]

            # Create the MD5 hash of the sequence number, client timestamp, server timestamp, and a secret key
            h = hashlib.md5('seq:{0},c_time:{1},s_time:{2},key:{3}'.format(seq, c_time, str(s_time), 'randomkey').encode()).hexdigest()
            print(m)

            # Create the response message
            # Example resposne: Reply 3 1696804876.324 1696804876.567 d41d8cd98f00b204e9800998ecf8427e6
            resp = 'Reply {0} {1} {2} {3}\n'.format(seq, c_time, str(s_time), h)
            # Otherwise, the server responds
            serverSocket.sendto(resp.encode(), address)

        except KeyboardInterrupt:
            serverSocket.close()
            sys.exit()
        except:
            continue

if __name__ == '__main__':
    serve(12000)