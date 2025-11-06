from socket import *
import os
import struct
import sys
import time
import select

ICMP_ECHO_REQUEST = 8

# Calculate the checksum of the packet
def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += string[len(string) - 1]
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum += (csum >> 16)
    answer = ~csum
    answer &= 0xffff
    answer = (answer >> 8) | ((answer << 8) & 0xff00)
    return answer

# Receive the ping response
def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    # Wait for the socket to be ready for reading
    while True:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)

        # Timeout
        if whatReady[0] == []:
            return (None, None)

        # Receive the packet
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # Fetch the ICMP header from the IP packet
        # The IP header is 20 bytes, so the ICMP header starts at byte 20
        icmpHeader = recPacket[20:28]

        # Unpack the ICMP header
        icmpType, icmpCode, icmpChecksum, icmpPacketID, icmpSequence = struct.unpack("bbHHh", icmpHeader)

        # Extract the data portion of the ICMP packet
        # The data portion starts at byte 28 and is 8 bytes long
        # The time sent is packed as a double (8 bytes)
        icmpData = recPacket[28:36]
        timeSent = struct.unpack("d", icmpData)[0]

        # Check if this is the reply we are waiting for
        # ID must match
        if icmpPacketID == ID:
            # Calculate the delay in milliseconds
            delay = (timeReceived - timeSent) * 1000
            # Return the delay and the ICMP fields as a tuple
            return (delay, (icmpType, icmpCode, icmpChecksum, icmpPacketID, icmpSequence, timeSent))
        
        # Adjust the time left for the next select call
        timeLeft -= howLongInSelect
        # If the time left is less than or equal to 0, we timed out
        if timeLeft <= 0:
            return (None, None)

# Send the ping request
def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    myChecksum = 0

    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())

    # Calculate the checksum on the data and the dummy header
    myChecksum = checksum(header + data)

    # Get the right checksum, and put it in the header
    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)
    
    # Rebuild the header with the correct checksum
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data
    mySocket.sendto(packet, (destAddr, 1))

# Perform one ping to the destination address
def doOnePing(destAddr, timeout):
    # Create a raw socket
    icmp = getprotobyname("icmp")
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    # Get the process ID to use as the packet ID
    myID = os.getpid() & 0xFFFF

    # Send the ping request
    sendOnePing(mySocket, destAddr, myID)
    
    # Receive the ping response
    result = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return result

# Ping the host multiple times
def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client or the server is lost
    dest = gethostbyname(host)
    resps = []
    print("Pinging " + dest + " using Python:")
    print("")

    # Send ping requests to a server separated by approximately one second
    for i in range(0, 5):
        result = doOnePing(dest, timeout)
        resps.append(result)
        if result[0] is not None:
            print(f"Ping {i + 1}: {result[0]:.2f} ms")
        else:
            print(f"Ping {i + 1}: Request timed out.")
        time.sleep(1)
    return resps

if __name__ == '__main__':
    ping("google.co.il")