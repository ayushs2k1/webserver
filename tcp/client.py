from socket import *
import sys

if len (sys.argv) != 4:
    print("Usage: python client.py <server_host> <server_port> <filename>")
    sys.exit(1)

server_host = sys.argv[1]
server_port = int(sys.argv[2])
filename = sys.argv[3]

# Create a TCP socket
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((server_host, server_port))

# Send HTTP GET request
request = f"GET /{filename} HTTP/1.1\r\nHost: {server_host}\r\n\r\n"
clientSocket.send(request.encode())

# Receive the response from the server
response = clientSocket.recv(4096).decode()
print("Response from server: ")
print(response)

clientSocket.close()