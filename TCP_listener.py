 #!/usr/bin/env python
 
import socket
import struct
from SAS_TM_Parser import heroesPacket
 
TCP_IP = '127.0.0.1'
TCP_PORT = 8000
BUFFER_SIZE = 2048
 
tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_sock.connect((TCP_IP, TCP_PORT))

print "connected to", TCP_IP, ":", TCP_PORT

data = ''
packet = heroesPacket()

data = tcp_sock.recv(BUFFER_SIZE)
print "Got some data: ", len(data), " bytes"
print "Raw: ", data
tcp_sock.close()

