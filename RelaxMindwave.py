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
Fs=128
show=False

# Please provide the number of sample points to take
if (len(sys.argv) > 1):
    samplepoints = int(sys.argv[1])
else:
    samplepoints = Fs*lamdalength


# def windowing(window, N):
#     if len(window)>=N:
#     if not False:
#         awindow = np.asarray( window )
#         fullsignal = fullsignal + window
#         afullsignal = np.asarray( fullsignal )

#         if (len(fullsignal) > 0):
#             awindow = awindow - afullsignal.mean(0)

#         o1 = psd(awindow[:,0])
#         o2 = psd(awindow[:,1])

#         print (o1, o2)

#         features.append( [o1, o2] )

#     # Slide window
#     window = window[N/2:N]
#     #window = window[1:N]

print ('Please remove the VGA connection that sometimes interfere with Mindwave')

import numpy as np
import mindwave, time


#headset = mindwave.Headset('/dev/tty.MindWaveMobile-DevA','ef47')
headset = mindwave.OfflineHeadset()

time.sleep(2)

plotter = Plotter(500,-500,5000)

attention = 0
meditation = 0
eeg = 0


ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S')
filename = './data/eeg.'+st+'.dat'
f = open(filename, 'w')

window = []
N = 128

try:
    while (headset.poor_signal > 5):
        print ("Headset signal noisy %d. Adjust the headset to fit better to your forehead and check earclip." % (headset.poor_signal))

    print ("Writing %d seconds output to %s" % (lamdalength,filename))
    for i in range(0,samplepoints):
        #time.sleep(.01)
        headset.dequeue()
        (count,eeg, attention, meditation, blink) = (headset.count, headset.raw_value, headset.attention, headset.meditation, headset.blink)

        window.append( int(eeg) )

        if len(window) > N:
            window = window[N/2:N]

        awindow = np.asarray(window)
        blink = np.sum(np.abs(awindow[0:N/2]))

        plotter.plotdata( [eeg, 0, 0, blink])
        #plotter.plotdata( [eeg, 0, 0])
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S.%f')
        f.write( str(st) + ' ' + str(eeg) + ' ' + str(attention) + ' ' + str(meditation) + ' ' + str(blink) + '\n')


finally:
    headset.stop()
    f.close()
