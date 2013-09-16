"""
Listen to serial, return most recent numeric values
Lots of help from here:
http://stackoverflow.com/questions/1093598/pyserial-how-to-read-last-line-sent-from-serial-device
"""
from threading import Thread
import time
import socket
import datetime
import numpy as np

last_received = ''
timer = 0

now_string = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
f = open('data_' + now_string + '.txt', 'w')

def receiving(ser):
    global last_received
    buffer = ''
    while True:
        buffer = buffer + ser.read(ser.inWaiting())
        if '\n' in buffer:
            lines = buffer.split('\n') # Guaranteed to have at least 2 entries
            last_received = lines[-2]
            #If the Arduino sends lots of empty lines, you'll lose the
            #last filled line, so you could make the above statement conditional
            #like so: if lines[-2]: last_received = lines[-2]
            buffer = lines[-1]


class UPDReceiver(object):
    def __init__(self, init=50):
        #try:
            self.UDP_IP = "127.0.0.1"
            self.UDP_Port = 2003
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.UDP_IP,self.UDP_Port))
            
            self.rawpacket = self.zeros(1024,int)
            
        #except serial.serialutil.SerialException:
            #no serial connection
            #self.ser = None
        #else:
            #Thread(target=receiving, args=(self.ser,)).start()
        
    def next(self):
        self.rawpacket, addr = self.sock.recvfrom(1024)
            
        
    def __del__(self):
        if self.ser:
            self.ser.close()

if __name__=='__main__':
    s = SerialData()
    for i in range(500):
        time.sleep(1)
        print s.next()