from SAS_TM_Parser import SAS_TM_Parser as parser
import numpy as np
sock = parser()
labels = sock.labels
while True:
    data = sock.next()
    if len(data) != len(labels):
        print "you done goofed"
        break
    time = sock.timestamps
    print "Time: ", (time - (np.floor(time)))
    print "Packets Received: ", sock.numpackets
    print "Packet SeqNumber: ", sock.sequence
    for plot in range (0, len(data)):
        for channel in range(0, len(data[plot][:])):
            print labels[plot][channel], ": ", data[plot][channel]

        
