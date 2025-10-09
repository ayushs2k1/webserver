from socket import *
import time
import random

def heartbeat(host, port, interval=1, count=10):
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    
    seq=1

    try:
        while True:
            # Check if the count limit has reached
            if count > 0 and seq > count:
                break

            # Simulate random client timeout (20% chance)
            if random.random() < 0.2:
                time.sleep(random.uniform(6,10))

            # Create the heartbeat message
            send_time = time.time()
            message = 'Heartbeat {0} {1}\n'.format(seq, send_time)
            try:
                clientSocket.sendto(message.encode(), (host, port))
            except Exception as e:
                print(f"Error sending heartbeat: {e}")

            # Increment the sequence number
            seq += 1
            
            # Wait for the interval before sending the next heartbeat
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nHeartbeat client stopped.")

    finally:
        clientSocket.close()

if __name__ == '__main__':
    heartbeat('localhost', 12000)



