from socket import *
import sys
import os
import shutil
import select
import hashlib

cacheDir = os.path.join(os.path.dirname(__file__), 'cache')

# For WINDOWS: can't keyboard interrupt while the program is in a blocking call
# Workaround is to timeout a blocking call every timeLeft seconds so the program can
# respond to any SIGINT or SIGKILL signals
# Shouldn't be a problem on Mac or Linux
# Additional note for WINDOWS: select.select() only works on sockets, so waitable should be a socket
def wait_interruptible(waitable, timeLeft):
    while True:
        ready = select.select([waitable], [], [], timeLeft)
        if len(ready[0]) > 0:
            return

# interruptible versions of accept(), recv(), readline(), read()
def interruptible_accept(socket):
    wait_interruptible(socket, 5)
    return socket.accept()

def interruptible_recv(socket, nbytes):
    wait_interruptible(socket, 5)
    return socket.recv(nbytes)

def interruptible_readline(fileObj):
    wait_interruptible(fileObj, 5)
    return fileObj.readline()

def interruptible_read(fileObj, nbytes=-1):
    wait_interruptible(fileObj, 5)
    return fileObj.read(nbytes)

# Read an HTTP message from a socket file object and parse it
# sockf: Socket file object to read from
# Returns: (headline: str, [(header: str, header_value: str)])
def parse_http_headers(sockf):
    # Read the first line from the HTTP message
    # This will either be the Request Line (request) or the Status Line (response)
    headline = interruptible_readline(sockf).decode().strip()

    # Set up list for headers
    headers = []
    while True:
        # Read a line at a time
        header = interruptible_readline(sockf).decode()
        # If it's the empty line '\r\n', it's the end of the header section
        if len(header.rstrip('\r\n')) == 0:
            break

        # Partition header by colon
        headerPartitions = header.partition(':')

        # Skip if there's no colon
        if headerPartitions[1] == '':
            continue

        headers.append((headerPartitions[0].strip(), headerPartitions[2].strip()))

    return(headline, headers)

# Forward a server response to the client and save to cache
# sockf: Socket file object connected to server
# fileCachePath: Path to cache file
# clisockf: Socket file object connected to client
def forward_and_cache_response(sockf, fileCachePath, clisockf):
    cachef = None

    # Create the intermediate directories to the cache file
    if fileCachePath is not None:
        os.makedirs(os.path.dirname(fileCachePath), exist_ok=True)
        # Open/create cache file
        cachef = open(fileCachePath, 'w+b')

    try:
        # Read response from server
        statusLine, headers = parse_http_headers(sockf)
        # Filter out the Connection header from the server
        headers = [h for h in headers if h[0] != 'Connection']
        # Replace with our own Connection header
        # We will close all connections after sending the response.
        # This is an inefficient,  single-threaded proxy!
        headers.append(('Connection', 'close'))
        # Fill in start.
        
        # Write status line to client and cache
        statusLineBytes = (statusLine + '\r\n').encode()
        clisockf.write(statusLineBytes)
        if cachef is not None:
            cachef.write(statusLineBytes)
        
        # Write headers to client and cache
        for header in headers:
            headerLine = f'{header[0]}: {header[1]}\r\n'.encode()
            clisockf.write(headerLine)
            if cachef is not None:
                cachef.write(headerLine)
        
        # Write empty line to separate headers from body
        clisockf.write(b'\r\n')
        if cachef is not None:
            cachef.write(b'\r\n')
        
        # Get Content-Length if present
        contentLength = None
        for header in headers:
            if header[0].lower() == 'content-length':
                contentLength = int(header[1])
                break
        
        # Read and forward body
        if contentLength is not None:
            # If content length is known, read that many bytes
            bytesLeft = contentLength
            while bytesLeft > 0:
                chunkSize = min(4096, bytesLeft)
                bodyChunk = interruptible_read(sockf, chunkSize)
                if not bodyChunk:
                    break
                clisockf.write(bodyChunk)
                if cachef is not None:
                    cachef.write(bodyChunk)
                bytesLeft -= len(bodyChunk)
        else:
            # If content length is not known, read until EOF
            while True:
                bodyChunk = interruptible_read(sockf, 4096)
                if not bodyChunk:
                    break
                clisockf.write(bodyChunk)
                if cachef is not None:
                    cachef.write(bodyChunk)
        
        clisockf.flush()

        # Fill in end.
    except Exception as e:
        print(e)
    finally:
        if cachef is not None:
            cachef.close()

# Forward a client request to a server
# sockf: Socket file object connected to server
# requestUri: The request URI to request from the server
# hostn: The Host header value to include in the forwarded request
# origRequestLine: The Request Line from the original client request
# origHeaders: The HTTP headers from the original client request
def forward_request(sockf, requestUri, hostn, origRequestLine, origHeaders):
    # Filter out the original Host header and replace it with our own
    headers = [h for h in origHeaders if h[0] != 'Host']
    headers.append(('Host', hostn))
    # Send request to the server
    # Fill in start.

    # Parse the original request line
    requestLineParts = origRequestLine.split()
    method = requestLineParts[0]
    version = requestLineParts[2]

    # Write request line
    newRequestLine = f'{method} {requestUri} {version}\r\n'
    sockf.write(newRequestLine.encode())

    # Write headers
    for header in headers:
        headerLine = f'{header[0]}: {header[1]}\r\n'
        sockf.write(headerLine.encode())

    # Write empty line to end headers
    sockf.write(b'\r\n')
    sockf.flush()

    # Fill in end.

def proxyServer(port):
    if os.path.isdir(cacheDir):
        shutil.rmtree(cacheDir)
    # Create a server socket, bind it to a port and start listening
    tcpSerSock = socket(AF_INET, SOCK_STREAM)

    # Fill in start.
    
    tcpSerSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    tcpSerSock.bind(('', port))
    tcpSerSock.listen(5)

    # Fill in end.

    tcpCliSock = None
    try:
        while 1:
            # Start receiving data from the client
            print('Ready to serve...')
            tcpCliSock, addr = interruptible_accept(tcpSerSock)

            print('Received a connection from:', addr)
            cliSock_f = tcpCliSock.makefile('rwb', 0)

            # Read and parse request from client
            requestLine, requestHeaders = parse_http_headers(cliSock_f)
            print(requestLine)

            if len(requestLine) == 0:
                continue

            # Extract the request URI from the given message
            requestUri = requestLine.split()[1]

            # if a scheme is included, split off the scheme, otherwise split off a leading slash
            uri_parts = requestUri.partition('http://')
            if uri_parts[1] == '':
                filename = requestUri.partition('/')[2]
            else:
                filename = uri_parts[2]

            print(f'filename: {filename}')

            if len(filename) > 0:
                # Compute the path to the cache file from the request URI
                # Change for Part Three
                fileCachePath = None
                cached = False
                
                # Fill in start.
                # Extract the HTTP method
                method = requestLine.split()[0]
                
                # Only cache GET requests (not POST, PUT, DELETE, etc.)
                if method == 'GET':
                    # Create a hash of the filename to use as cache file name
                    filename_hash = hashlib.md5(filename.encode()).hexdigest()
                    fileCachePath = os.path.join(cacheDir, filename_hash)
                    # Check if cache file exists
                    cached = os.path.isfile(fileCachePath)
                # Fill in end.
                
                print(f'fileCachePath: {fileCachePath}')

                # Check whether the file exists in the cache
                if fileCachePath is not None and cached:
                    # Read response from cache and transmit to client
                    # Fill in start.

                    try:
                        with open(fileCachePath, 'r+b') as cachef:
                            data = cachef.read()
                            cliSock_f.write(data)
                            cliSock_f.flush()
                    except Exception as e:
                        print(e)

                    # Fill in end.
                    print('Read from cache')
                else:
                    # Create a socket on the ProxyServer
                    c = socket(AF_INET, SOCK_STREAM)
                    
                    hostn = filename.partition('/')[0]
                    print(f'hostn: {hostn}')

                    # Fill in start.

                    # Parsing host name and port number
                    if ':' in hostn:
                        hostname, portn = hostn.split(':')
                        portn = int(portn)
                    else:
                        hostname = hostn
                        portn = 80
                    
                    # Fill in end.

                    try:
                        # Connect to the socket
                        # Fill in start.

                        c.connect((hostname, portn))

                        # Fill in end.

                        # Create a temporary file on this socket and ask port 80 for the file requested by the client
                        fileobj = c.makefile('rwb', 0)
                        
                        # For POST requests, read the body from client first
                        post_body = None
                        if method == 'POST':
                            content_length = None
                            for header in requestHeaders:
                                if header[0].lower() == 'content-length':
                                    content_length = int(header[1])
                                    break
                            
                            if content_length is not None and content_length > 0:
                                post_body = b''
                                bytes_remaining = content_length
                                while bytes_remaining > 0:
                                    chunk_size = min(4096, bytes_remaining)
                                    data = interruptible_read(cliSock_f, chunk_size)
                                    if len(data) == 0:
                                        break
                                    post_body += data
                                    bytes_remaining -= len(data)
                        
                        forward_request(fileobj, f'/{filename.partition("/")[2]}', hostn, requestLine, requestHeaders)
                        
                        # Send POST body after headers if present
                        if post_body is not None:
                            fileobj.write(post_body)
                            fileobj.flush()

                        # Read the response from the server, cache, and forward it to client
                        forward_and_cache_response(fileobj, fileCachePath, cliSock_f)
                    except Exception as e:
                        print(e)
                    finally:
                        c.close()
            tcpCliSock.close()
    except KeyboardInterrupt:
        pass

    # Close the server socket and client socket
    # Fill in start.

    if tcpCliSock is not None:
        tcpCliSock.close()
    tcpSerSock.close()

    # Fill in end.
    sys.exit()

if __name__ == "__main__":
    proxyServer(8888)