from socket import *
import os
import struct
import sys
import time
import select

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0

# ICMP Error Type Codes
ICMP_ERROR_CODES = {
    0: "Echo Reply",
    3: "Destination Unreachable",
    4: "Source Quench",
    5: "Redirect",
    8: "Echo Request",
    11: "Time Exceeded",
    12: "Parameter Problem",
    13: "Timestamp",
    14: "Timestamp Reply",
    15: "Information Request",
    16: "Information Reply"
}

# ICMP Destination Unreachable Subcodes
DEST_UNREACHABLE_CODES = {
    0: "Network Unreachable",
    1: "Host Unreachable",
    2: "Protocol Unreachable",
    3: "Port Unreachable",
    4: "Fragmentation Needed and DF Flag Set",
    5: "Source Route Failed",
    6: "Destination Network Unknown",
    7: "Destination Host Unknown",
    8: "Source Host Isolated",
    9: "Network Administratively Prohibited",
    10: "Host Administratively Prohibited",
    11: "Network Unreachable for ToS",
    12: "Host Unreachable for ToS",
    13: "Communication Administratively Prohibited",
    14: "Host Precedence Violation",
    15: "Precedence Cutoff in Effect"
}

# Time Exceeded Subcodes
TIME_EXCEEDED_CODES = {
    0: "Time to Live Exceeded in Transit",
    1: "Fragment Reassembly Time Exceeded"
}

# Redirect subcodes
REDIRECT_CODES = {
    0: "Redirect Datagram for the Network",
    1: "Redirect Datagram for the Host",
    2: "Redirect Datagram for the ToS & Network",
    3: "Redirect Datagram for the ToS & Host"
}

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

def parseICMPError(icmpType, icmpCode):
    error_msg = ICMP_ERROR_CODES.get(icmpType, "Unknown ICMP Type ({icmpType})")

    if icmpType == 3:  # Destination Unreachable
        subcode_msg = DEST_UNREACHABLE_CODES.get(icmpCode, f"Unknown Destination Unreachable Code ({icmpCode})")
        return f"{error_msg}: {subcode_msg}"
    
    elif icmpType == 11:  # Time Exceeded
        subcode_msg = TIME_EXCEEDED_CODES.get(icmpCode, f"Unknown Time Exceeded Code ({icmpCode})")
        return f"{error_msg}: {subcode_msg}"
    
    elif icmpType == 5:  # Redirect
        subcode_msg = REDIRECT_CODES.get(icmpCode, f"Unknown Redirect Code ({icmpCode})")
        return f"{error_msg}: {subcode_msg}"
    
    elif icmpCode != 0:
        return f"{error_msg}: Unknown Code ({icmpCode})"
    
    return error_msg

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
            return "timeout", None

        # Receive the packet
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # Fetch the ICMP header from the IP packet
        # The IP header is 20 bytes, so the ICMP header starts at byte 20
        icmpHeader = recPacket[20:28]

        # Unpack the ICMP header
        icmpType, icmpCode, icmpChecksum, icmpPacketID, icmpSequence = struct.unpack("bbHHh", icmpHeader)

        if icmpType != ICMP_ECHO_REPLY:
            error_description = parseICMPError(icmpType, icmpCode)
            return "error", {
                "icmpType": icmpType,
                "icmpCode": icmpCode,
                "error_description": error_description,
                "source": addr[0],
                "destination": destAddr[0],
                "checksum": icmpChecksum
            }
        

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
            return "success", {
                "delay": delay,
                "icmpType": icmpType,
                "icmpCode": icmpCode,
                "icmpChecksum": icmpChecksum,
                "icmpPacketID": icmpPacketID,
                "icmpSequence": icmpSequence,
                "timeSent": timeSent
            }

        # Adjust the time left for the next select call
        timeLeft -= howLongInSelect
        # If the time left is less than or equal to 0, we timed out
        if timeLeft <= 0:
            return "timeout", None

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
    try:
        dest = gethostbyname(host)
    except gaierror:
        print(f"Cannot resolve {host}: Unknown host")
        return
    
    print("Pinging " + dest + " using Python:")
    print("")

    rtts = []
    packets_sent = 0
    packets_received = 0
    errors = []

    # Send ping requests to a server separated by approximately one second
    for i in range(0, 5):
        packets_sent += 1
        status, result = doOnePing(dest, timeout)
        
        if status == "success":
            packets_received += 1
            rtt = result["delay"]
            rtts.append(rtt)
            print(f"Ping {i + 1}: {rtt:.2f} ms")
        elif status == "timeout":
            print(f"Ping {i + 1}: Request timed out.")
        elif status == "error":
            # Display detailed error information
            error_type = result["icmpType"]
            error_code = result["icmpCode"]
            error_desc = result["error_description"]
            error_source = result["source"]
            error_dest = result["destination"]
            print(f"Ping {i + 1}: ERROR - {error_desc} (Type: {error_type}, Code: {error_code}, Source: {error_source}, Destination: {error_dest})")
            errors.append({
                "icmpType": error_type,
                "icmpCode": error_code,
                "error_description": error_desc,
                "source": error_source,
                "destination": error_dest
            })
        elif status == "os_error":
            error_desc = result["error_description"]
            error_dest = result["destination"]
            print(f"Ping {i + 1}: OS ERROR - {error_desc} (Destination: {error_dest})")
            errors.append({
                "error_description": error_desc,
                "destination": error_dest
            })
        time.sleep(1)


    # Print statistics
    print("\n--- Ping statistics ---")
    print(f"{packets_sent} packets transmitted, {packets_received} packets received, ", end="")

    # Calculate packet loss percentage
    if packets_sent > 0:
        packet_loss = ((packets_sent - packets_received) / packets_sent) * 100
        print(f"{packet_loss:.1f}% packet loss")
    else:
        print("0.0% packet loss")

    # Calculate min/avg/max RTT
    if rtts:
        min_rtt = min(rtts)
        max_rtt = max(rtts)
        avg_rtt = sum(rtts) / len(rtts)
        print(f"rtt min/avg/max = {min_rtt:.2f}/{avg_rtt:.2f}/{max_rtt:.2f} ms")
    else:
        print("No replies received.")

    # Print error details if any
    if errors:
        print("\n--- Ping Errors ---")
        for error in errors:
            print(f"Type: {error['icmpType']}, Code: {error['icmpCode']}, Description: {error['error_description']}, Source: {error['source']}, Destination: {error['destination']}")

    print("")

if __name__ == '__main__':
    # Destination Unreachable: Network Unreachable
    ping("203.0.113.1")
