#coding: latin-1
#
# Run me with frameworkpython inside a virtual environment.
# Or install the environment.yml for Anaconda.

# This program uses Mindawave object to connect using bluetooth to Mindwave
# and get the raw eeg signals from there.
# 
# It also plot the signal using matplotlib.
#
# Fs = 128

import socket,select
import json

import time, datetime, sys

import matplotlib.pyplot as plt

import sys

lamdalength = 10
Fs=512
show=False

# Please provide the number of sample points to take
if (len(sys.argv) > 1):
    samplepoints = int(sys.argv[1])
else:
    samplepoints = Fs*lamdalength

print ('Please remove the VGA connection that sometimes interfere with Mindwave')


import mindwave, time

#headset = mindwave.Headset('/dev/tty.MindWaveMobile-DevA','ef47')
headset = mindwave.OfflineHeadset(sys.argv[2])

time.sleep(2)

from Plotter import Plotter
plotter = Plotter(500,-500,500)

attention = 0
meditation = 0
eeg = 0


ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S')
filename = './data/eeg.'+st+'.dat'
f = open(filename, 'w')

try:
    while (headset.poor_signal > 5):
        print("Headset signal noisy %d. Adjust the headset and earclip." % (headset.poor_signal))

    print("Writing %d seconds output to %s" % (lamdalength,filename))
    for i in range(0,samplepoints):
        #time.sleep(.01)
        headset.dequeue()
        (count,eeg, attention, meditation, blink) = (headset.count, headset.raw_value, headset.attention, headset.meditation, headset.blink)

        plotter.plotdata( [eeg, attention, meditation, blink])
        #plotter.plotdata( [eeg, 0, 0])
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S.%f')
        f.write( str(ts) + ' ' + str(count) + ' ' + str(eeg) + ' ' + str(attention) + ' ' + str(meditation) + ' ' + str(blink) + '\n')


finally:
    headset.stop()
    f.close()
