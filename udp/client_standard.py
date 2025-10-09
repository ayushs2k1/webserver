from socket import *
import time

def ping_standard(host, port):
    resps = []
    rtt_list = []
    
    # Create a UDP socket
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    # Set socket timeout as 1 second
    clientSocket.settimeout(1)

    sent = 0
    received = 0

    try:
        for seq in range(1, 11):
            send_time = time.time()
            message = 'Ping {0} {1}\n'.format(seq, send_time)
            sent += 1

            try:
                clientSocket.sendto(message.encode(), (host, port))
                response, address = clientSocket.recvfrom(1024)
                recv_time = time.time()
                rtt = recv_time - send_time

                response = response.decode().strip()

                resps.append((seq, response, rtt))
                rtt_list.append(rtt)
                received += 1

            except timeout:
                resps.append((seq, 'Request timed out', 0))
            except Exception as e:
                resps.append((seq, str(e), 0))
    finally:
        clientSocket.close()

    # Calculate statistics
    loss = ((sent - received) / sent) * 100

    if rtt_list:
        min_rtt = min(rtt_list)
        max_rtt = max(rtt_list)
        avg_rtt = sum(rtt_list) / len(rtt_list)
    else:
        min_rtt = max_rtt = avg_rtt = 0
    
    stats = {
        'sent': sent,
        'received': received,
        'loss %': loss,
        'minimum rtt': min_rtt,
        'maximum rtt': max_rtt,
        'average rtt': avg_rtt,
    }

    return resps, stats

if __name__ == '__main__':
    resps, stats = ping_standard('localhost', 12000)
    print(resps)
    print(stats)
