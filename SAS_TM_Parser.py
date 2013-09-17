"""
Listen to serial, return most recent numeric values
Lots of help from here:
http://stackoverflow.com/questions/1093598/pyserial-how-to-read-last-line-sent-from-serial-device
"""
#from threading import Thread
#import time
import socket
#import datetime
# from numpy import *
import numpy as np

import struct

last_received = ''
timer = 0

class heroesHeader:
    def __init__(self):
        self.syncWord = []
        self.payloadType = []
        self.source = []
        self.payloadLength = []
        self.checksum = []
        self.timesNano = []
        self.timeSec = []          
    
    def read(self, rawpacket = ''):
        if (len(rawpacket) >= 16):
            header = struct.unpack('=H2B2H2I',rawpacket[0:16])
            self.syncWord = header[0]
            self.payloadType = header[1]
            self.source = header[2]
            self.payloadLength = header[3]
            self.checksum = header[4]
            self.timesNano = header[5]
            self.timeSec = header[6]
            
            if (self.syncWord != 0xc39a):
                print "Invalid HEROES sync word: ", hex(self.syncWord)
                return False
            else:
                return True
        else:
            return False

class heroesPacket:
    def __init__(self):
        self.header = heroesHeader()
        self.payload = ''

    def read(self, rawpacket):
        valid = self.header.read(rawpacket)
        self.payload = rawpacket[16:]
        return vaild


class sasPacket(heroesPacket):
    def __init__(self):
        heroesPacket.__init__(self)
        self.syncWord = []
        self.telemSeqNum = []
        self.status = []
        self.cmdEcho = []
        self.housekeeping = []
        
        self.sasID = []
        
    def read(self, rawpacket):
        valid = self.header.read(rawpacket)
        if not valid: return 1
        if (self.header.source != 0x30):
            # print "Invalid source ID: ", hex(self.header.source)
            return False
        if (self.header.payloadType != 0x70):
            # print "Invalid payload type: ", hex(self.header.payloadType)
            return False
        if (self.header.payloadLength != 94):
            # print "Payload too short: ", hex(self.header.payloadLength)
            return False
        
        header = struct.unpack('=HIBH', rawpacket[16:25])
        self.syncWord = header[0]
        self.telemSeqNum = header[1]
        self.status = header[2]
        self.cmdEcho = header[3]
        if (self.syncWord == 0xeb90):
            self.sasID = 1
        elif (self.syncWord == 0xf626):
            self.sasID = 2
        else:
            # print "Not a SAS I know: ", hex(self.syncWord)
            return False

        self.housekeeping = list(struct.unpack('=2H', rawpacket[25:29]))
        roundRobinPos = self.telemSeqNum % 8
        for i in range (0, 2):
            if (roundRobinPos < 7):
                self.housekeeping[i] = (float(self.housekeeping[i])-8192)/8
                if (i == 0):
                    self.housekeeping[i] /= 10;
                else:
                    if (roundRobinPos < 2):
                        self.housekeeping[i] /= 10;
                    else:
                        self.housekeeping[i] /= 500;
            else:
                if (i == 0):
                    if (self.housekeeping[i] == 0):
                        self.housekeeping[i] = 'Not Synced'
                    else:
                        self.housekeeping[i] = 'Synced'
                else:
                    if (self.housekeeping[i] == 0): self.housekeeping[i] = 'Neither'
                    elif (self.housekeeping[i] == 1): self.housekeeping[i] = 'PYAS'
                    elif (self.housekeeping[i] == 2): self.housekeeping[i] = 'RAS'
                    elif (self.housekeeping[i] == 3): self.housekeeping[i] = 'Both'
                    else: self.housekeeping[i] = 'Father give me legs'

        return True

class SAS_TM_Parser(object):
    def __init__(self):
        #try:
        self.UDP_IP = ''
        self.UDP_Port = 2003
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.UDP_IP,self.UDP_Port))
            self.validsocket = True
        except:
            print "Can't create socket"
            self.validsocket = False
        
        self.rawpacket = ''
        
        self.numpackets = (0,0)
        self.timestamps = [],[]
        self.sequence = [],[]
        self.packet = sasPacket()
        self.housekeepingData = np.zeros((2,14),float)
        
        #except serial.serialutil.SerialException:
            #no serial connection
            #self.ser = None
        #else:
            #Thread(target=receiving, args=(self.ser,)).start()
        
    def next(self):
        if self.validsocket:        
            while True:
                self.rawpacket, addr = self.sock.recvfrom(1024)
                length = len(self.rawpacket)
                # print "Got a packet of length ", length
                valid = self.packet.read(self.rawpacket)
                if valid:
                    sas = self.packet.sasID -1
                    idx = self.packet.telemSeqNum % 8
                    # print "SAS: ", sas+1, " HKidx: ", idx, " Data: ", self.packet.housekeeping[0], " ", self.packet.housekeeping[1]
                    if (idx < 7):
                        self.housekeepingData[sas][idx] = self.packet.housekeeping[0]
                        self.housekeepingData[sas][7 + idx] = self.packet.housekeeping[1]
                        print self.housekeepingData
                        print "\r\r\r\r"
                        return self.housekeepingData
        else:
            self.housekeepingData[0] = self.housekeepingData[0]+[0.2,0.2,0.2,0.2,0.2,0.2,0.2]
            self.housekeepingdata[1] = self.housekeepingData[1]+[0.2,0.2,0.2,0.2,0.2,0.2,0.2]
    def __del__(self):
        self.sock.close()
