"""
Listen to serial, return most recent numeric values
Lots of help from here:
http://stackoverflow.com/questions/1093598/pyserial-how-to-read-last-line-sent-from-serial-device
"""
from threading import Thread
import time
import serial
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


class SerialData(object):
    def __init__(self, init=50):
        try:
            self.ser = ser = serial.Serial(
                port='/dev/tty.usbmodem1411',
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
                xonxoff=0,
                rtscts=0,
                interCharTimeout=None
            )
        except serial.serialutil.SerialException:
            #no serial connection
            self.ser = None
        else:
            Thread(target=receiving, args=(self.ser,)).start()
        
    def next(self):
    	global timer
    	global f
        if not self.ser:
            return 'bad' #return anything so we can test when Arduino isn't connected
        #return a float value or try a few times until we get one
        for i in range(40):
            raw_line = last_received
            try:
                time_str = datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")
                timer = timer + 1
                if( (timer % 6) == 0):
                	f.write(time_str + ',' + raw_line + '\n')
                	print('wrote to file')
                data = np.array(raw_line.split(','), dtype='|S4')
                print(data.astype(np.float))
                return data.astype(np.float)
            except ValueError:
                print 'bogus data',raw_line
                time.sleep(.05)
        return 0.
    def __del__(self):
        if self.ser:
            self.ser.close()

if __name__=='__main__':
    s = SerialData()
    for i in range(500):
        time.sleep(1)
        print s.next()