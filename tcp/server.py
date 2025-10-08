# Simple web server that handles one HTTP request at a time

# Import socket module
from socket import *
# In order to terminate the program
import sys

def webServer(port=6789):
    # Create an IPv4 TCP socket
    serverSocket = socket(AF_INET, SOCK_STREAM)

    # Prepare a server socket
    serverSocket.bind(('', port))
    serverSocket.listen(1)
    try:
        while True:
            # Establish the connection
            print('Ready to serve...')
            connectionSocket, addr = serverSocket.accept()
            try:
                message = connectionSocket.recv(1024).decode()

                # Skip empty or malformed requests
                if not message or len(message.split()) < 2:
                    connectionSocket.close()
                    continue

                filename = message.split()[1]
                f = open(filename[1:])
                outputdata = f.read()
                f.close()

                # Send one HTTP header line into socket
                header = 'HTTP/1.1 200 OK\r\n\r\n'
                connectionSocket.send(header.encode())

                # Send the content of the requested file to the client
                #try:
                for i in range(0, len(outputdata)):
                    connectionSocket.send(outputdata[i].encode())
                
                connectionSocket.close()

            except IOError:
                # Send response message for file not found
                header = 'HTTP/1.1 404 Not Found\r\n\r\n'
                connectionSocket.send(header.encode())
                connectionSocket.send(b"<html><body><h1>404 Not Found</h1></body></html>")

                # Close client socket
                connectionSocket.close()

    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        serverSocket.close()
        sys.exit(0)

if __name__ == "__main__":
    webServer(6789)
            