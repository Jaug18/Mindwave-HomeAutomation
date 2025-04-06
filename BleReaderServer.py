#coding: latin-1
#
# Run me with frameworkpython inside a virtual environment.

# This program connects to Neurosky Mindwave Mobile (the black version) using
# bluetooth (bluetooth to serial connection). It does not need the TGC server
# running on the computer thanks to mindwave.py code that can handle the comm
# protocol.

# At the same time this piece of code set up a multiclient TCP/IP server on port
# 13855 so that the same data can be shared among many clients.

import socket, select
import json

import time, datetime, sys

import matplotlib.pyplot as plt

class Plotter:

    def __init__(self,rangeval,minval,maxval):
        # You probably won't need this if you're embedding things in a tkinter plot...
        import matplotlib.pyplot as plt
        plt.ion()

        self.x = []
        self.y = []
        self.z = []

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)

        self.line1, = self.ax.plot(self.x,'r', label='X') # Returns a tuple of line objects, thus the comma
        self.line2, = self.ax.plot(self.y,'g', label='Y')
        self.line3, = self.ax.plot(self.z,'b', label='Z')

        self.rangeval = rangeval
        self.ax.axis([0, rangeval, minval, maxval])
        self.plcounter = 0
        self.plotx = []

    def plotdata(self,new_values):
        # is  a valid message struct
        #print new_values

        self.x.append( float(new_values[0]))
        self.y.append( float(new_values[1]))
        self.z.append( float(new_values[2]))

        self.plotx.append( self.plcounter )

        self.line1.set_ydata(self.x)
        self.line2.set_ydata(self.y)
        self.line3.set_ydata(self.z)

        self.line1.set_xdata(self.plotx)
        self.line2.set_xdata(self.plotx)
        self.line3.set_xdata(self.plotx)

        self.fig.canvas.draw()
        plt.pause(0.0001)

        self.plcounter = self.plcounter+1

        if self.plcounter > self.rangeval:
          self.plcounter = 0
          self.plotx[:] = []
          self.x[:] = []
          self.y[:] = []
          self.z[:] = []


import mindwave, time

# Hardcoded serial number of my Mindwave device.
headset = mindwave.Headset('/dev/tty.MindWaveMobile-DevA','ef47')

time.sleep(2)

plotter = Plotter(500,-500,500)

attention = 0
meditation = 0
eeg = 0

# def on_raw( headset, rawvalue):
#     time.sleep(.01)
#     print "Count %d :Raw value: %s, Attention: %s, Meditation: %s" % (headset.count, headset.raw_value, headset.attention, headset.meditation)
#     (eeg, attention, meditation) = (headset.raw_value, headset.count, headset.meditation)
#     plotter.plotdata( [eeg, attention, meditation])
#
# headset.raw_value_handlers.append( on_raw )

conn_list = []
serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('0.0.0.0', 13855)
serversock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
print >> sys.stderr, 'Starting up on %s port %s', server_address
serversock.bind(server_address)
serversock.listen(10)

conn_list.append( serversock )


ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S')
filename = './data/eeg.'+st+'.dat'
f = open(filename, 'w')

while (headset.poor_signal > 5):
    print ("Headset signal noisy %d. Adjust the headset to adjust better to your forehead." % (headset.poor_signal))

try:
    counter = 0
    print ("Writing output to "+filename)
    while (True):
        time.sleep(.01)
        (eeg, attention, meditation) = (headset.raw_value, headset.attention, headset.meditation)
        #plotter.plotdata( [eeg, attention, meditation])
        plotter.plotdata( [eeg, attention, meditation])

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S.%f')
        f.write( str(st) + ' ' + str(eeg) + ' ' + str(attention) + ' ' + str(meditation) + '\n')

        read_sockets,write_sockets,error_sockets = select.select(conn_list, [],[])

        for connsock in read_sockets:
            if connsock == serversock:
                sockfd, addr = serversock.accept()
                conn_list.append( sockfd )
                print ("Client (%s, %s) connected " % addr)

            else:
                try:
                    sent = connsock.send(str(eeg) + ' ' + str(attention) + ' ' + str(meditation) +  ' ' + str(counter) + '\r\n')

                except:
                    print  ("Client (%s, %s) is offline " % addr)
                    connsock.close()
                    conn_list.remove(connsock)
                    continue

        counter = counter + 1
        if (counter >= 256):
            counter = 0
except Exception as e:
    print (e)
finally:
    headset.disconnect()
    headset.serial_close()
    f.close()
    serversock.close()


try:
    headset.disconnect()
    headset.serial_close()
    print ('Serial released')
finally:
    pass

try:
    f.close()
    sock.close()
    serversock.close()
    print ('Socket released')
finally:
    pass
