from SAS_TM_Parser import SAS_TM_Parser as parser
import numpy as np
import time
import datetime as YES
sock = parser()
labels = sock.labels
while True:
    data, time = sock.next()
    if len(data) != len(labels):
        print "you done goofed"
        break
    
    print "Packets Received: ", sock.numpackets
    print "Packet SeqNumber: ", sock.sequence
    for plot in range (len(data)):
        for channel in range(len(data[plot])):
            print "@", YES.datetime.fromtimestamp(time[plot][channel]), ": ", data[plot][channel]
    time.wait(.1)
