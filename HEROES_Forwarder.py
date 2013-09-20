 #!/usr/bin/env python
 
import socket
import struct
from SAS_TM_Parser import heroesPacket
 
TCP_IP = '192.168.0.100'
TCP_PORT = 8000
BUFFER_SIZE = 2048
 
UDP_IP = "127.0.0.1"
UDP_PORT = 1337


tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_sock.connect((TCP_IP, TCP_PORT))

udp_sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP

print "connected to", TCP_IP, ":", TCP_PORT

data = ''
packet = heroesPacket()

while True:
    data += tcp_sock.recv(BUFFER_SIZE)
    for k in range(len(data)-1):
        if len(data[k:k+2]) == 2:
            word = struct.unpack('=H', data[k:k+2])
            if (word[0] == 0xc39a):
                rawPacket = data[0:k]
                data = data[k:len(data)]
                if (packet.read(rawPacket)):
                    udp_sock.sendto(rawPacket, (UDP_IP, UDP_PORT))
                    

s.close()

