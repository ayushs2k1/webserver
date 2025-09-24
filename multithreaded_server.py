from socket import *
import threading
import sys

def handle_client(connectionSocket):
    try:
        message = connectionSocket.recv(1024).decode()

        # Skip empty or malformed requests
        if not message or len(message.split()) < 2:
            connectionSocket.close()
            return
        
        filename = message.split()[1]
        f = open(filename[1:])
        outputdata = f.read()
        f.close()

        # Send one HTTP header line into socket
        header = 'HTTP/1.1 200 OK\r\n\r\n'
        connectionSocket.send(header.encode())

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

def webServer(port=6789):
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('', port))
    # Allow up to 5 queued connections
    serverSocket.listen(5)

    thread_count = 0

    try:
        while True:
            print('Ready to serve...')
            connectionSocket, addr = serverSocket.accept()
            thread_count += 1
            client_thread = threading.Thread(target=handle_client, args=(connectionSocket,), name=f"ClientThread-{thread_count}")
            client_thread.daemon = True
            client_thread.start()

            # Print the number of active threads
            print(f"Started thread {client_thread.name} for client {addr}")
    
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        serverSocket.close()
        sys.exit(0)

if __name__ == "__main__":
    webServer(6789)
