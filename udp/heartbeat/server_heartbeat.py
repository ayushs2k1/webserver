from socket import *
import socket
import sys
import time

def serve(port, timeout=5):
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.bind(('', port))
    serverSocket.settimeout(1)

    # Dictionary to track each client's last heartbeat
    # Key: client address, Value: (last seq, last timestamp, expected next seq)
    client = {}

    while True:
        try:
            message, address = serverSocket.recvfrom(1024)
            recv_time = time.time()

            # Parse the heartbeat message
            # Example message: "Heartbeat 3 1696804876.324" → ['Heartbeat', '3', '1696804876.324']
            try:
                m = message.decode().split()
                if len(m) >= 3 and m[0] == 'Heartbeat':
                        seq = int(m[1])
                        client_time = float(m[2])
                else:
                    print(f"[{address}] Invalid heartbeat format: {message.decode().strip()}")
                    continue
            except (ValueError, IndexError):
                print(f"[{address}] ERROR: Could not parse heartbeat: {message.decode().strip()}")
                continue

            # Calculate the one-way delay
            one_way_delay = recv_time - client_time

            # Check if this is a known client
            if address in client:
                print(f'[{address}] Heartbeat seq = {seq}, One-way delay = {one_way_delay * 1000:.2f} ms')
            else:
                print(f'[{address}] New client connected. Heartbeat seq = {seq}, One-way delay = {one_way_delay * 1000:.2f} ms')

            # Update client tracking info
            client[address] = (seq, recv_time)

        except socket.timeout:
            # Check for clients that have timed out
            current_time = time.time()
            dead_clients = []

            for address, (last_seq, last_time) in client.items():
                time_since_heartbeat = current_time - last_time
                if time_since_heartbeat > timeout:
                    print(f'[{address}] CLIENT TIMEOUT: No heartbeat received for {time_since_heartbeat:.2f} seconds (Last seq: {last_seq})')
                    dead_clients.append(address)

            # Remove dead clients
            for address in dead_clients:
                del client[address]

        except KeyboardInterrupt:
            print("\n Heartbeat server stopped.")
            serverSocket.close()
            sys.exit()
        
        except Exception as e:
            print(f"Error: {e}")
            continue

if __name__ == '__main__':
    serve(12000)