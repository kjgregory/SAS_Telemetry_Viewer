"""
Listen to serial, return most recent numeric values
Lots of help from here:
http://stackoverflow.com/questions/1093598/pyserial-how-to-read-last-line-sent-from-serial-device
"""
#from threading import Thread
#import time
import socket
#import datetime
from numpy import *
#import numpy as np

last_received = ''
timer = 0

class UDPReceiver(object):
    def __init__(self):
        #try:
            self.UDP_IP = "127.0.0.1"
            self.UDP_Port = 2003
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.UDP_IP,self.UDP_Port))
            
            self.rawpacket = zeros(1024,int)
            
            self.numpackets = (0,0)
            self.timestamps = [],[]
            self.sequence = [],[]
            
            #finish implementing the rest of the packet later... this will help us get to a working temperature display sooner            
            self.housekeeping = ([],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]),([],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[])
            #self.suncenterx = ([],[]),([],[])
            #self.suncentery = ([],[]),([],[])
            #self.scerrorx = [],[]
            #self.scerrory = [],[]
            #self.limb. = [],[]
            #self.limby = [],[]
            #self.numfiducials = [],[]
            #self.numlimbs = [],[]
            #self.fiducialsx = ([],[],[],[],[],[]),([],[],[],[],[],[])
            #self.fiducialsy = ([],[],[],[],[],[]),([],[],[],[],[],[])
            #self.px2scx = ([],[]),([],[])
            #self.px2scy = ([],[]),([],[])
            
            
        #except serial.serialutil.SerialException:
            #no serial connection
            #self.ser = None
        #else:
            #Thread(target=receiving, args=(self.ser,)).start()
        
    def parse(self):
        while True:
            self.rawpacket = zeros(1024,int)        
            while (self.rawpacket[3] != 0x30) | ((self.rawpacket[16:18] != [0xeb,0x90])&(self.rawpacket[16:18] != [0xf6,0x26])):
                self.rawpacket, addr = self.sock.recvfrom(1024)
            if self.rawpacket[16:18] == (0xeb,0x90):
                sasnum = 0
            else:
                sasnum = 1
            self.timestamps[sasnum].append(0)
            for i in range(12,16):            
                self.timestamps[sasnum][self.numpackets] = self.timestamps[sasnum][self.numpackets] + (self.rawpacket[i] << (8*(15-i)))
            self.sequence[sasnum].append(0)
            for i in range(18,22):
                self.sequence[sasnum] = self.sequence[sasnum] + (self.rawpacket[i] << (8*(21-i)))
            #TODO: stick nano-seconds into the timestamps list here...
            hknum = self.sequence[sasnum] & 0xf
            for i in range(0,8):
                if i == hknum:
                    self.housekeeping[sasnum][i] = (self.rawpacket[25] << 8) + self.rawpacket[26]
                elif self.numpackets[sasnum] == 0:
                    self.housekeeping[sasnum][i] = 0
                else:
                    self.housekeeping[sasnum][i] = self.housekeeping[sasnum][i-1]
            for i in range(8,16):
                if i == hknum + 8:
                    self.housekeeping[sasnum][i] = (self.rawpacket[27] << 8) + self.rawpacket[28]
                elif self.numpackets[sasnum] == 0:
                    self.housekeeping[sasnum][i] = 0
                else:
                    self.housekeeping[sasnum][i] = self.housekeeping[sasnum][i-1]
                    
            self.numpackets[sasnum] = self.numpackets[sasnum] + 1
            print "packet", sasnum, self.numpackets[sasnum], self.sequence[sasnum]
                        
        
    def __del__(self):
        self.sock.close()
