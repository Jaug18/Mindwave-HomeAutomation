#coding: latin-1

import socket,select
import json

import time, datetime, sys

import matplotlib.pyplot as plt

import sys

import pyaudio
volume = 0.5     # range [0.0, 1.0]
fs = 44100       # sampling rate, Hz, must be integer
duration = 0.01   # in seconds, may be float
fwave = 440.0        # sine frequency, Hz, may be float

p = pyaudio.PyAudio()

stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=fs,
                output=True)

lamdalength = 10
Fs=128
show=False

# Please provide the number of sample points to take
if (len(sys.argv) > 1):
    samplepoints = int(sys.argv[1])
else:
    samplepoints = Fs*lamdalength

print('Please remove the VGA connection that sometimes interfere with Mindwave')

import numpy as np
import mindwave, time
import matplotlib.image as mpimg

from Plotter import Plotter

#headset = mindwave.Headset('/dev/tty.MindWaveMobile-DevA','ef47')
filename='blinking.dat'
headset = mindwave.OfflineHeadset(filename)

time.sleep(2)

plotter = Plotter(500,-500,500)

attention = 0
meditation = 0
eeg = 0


ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S')
logfilename = './data/eeg.'+st+'.dat'
f = open(logfilename, 'w')

window = []
N = 128
signaleeg = []

plt.title(filename)
try:
    while (headset.poor_signal > 5):
        print("Headset signal noisy %d. Adjust the headset and the earclip." % (headset.poor_signal))

    print("Writing %d seconds output to %s" % (lamdalength,logfilename))
    for i in range(0,samplepoints):
        #time.sleep(.01)
        headset.dequeue()
        (count,eeg, attention, meditation, blink) = (headset.count, headset.raw_value, headset.attention, headset.meditation, headset.blink)

        window.append( int(eeg) )
        signaleeg.append( int (eeg) )

        if len(window) > N:
            window = window[N/2:N]

        awindow = np.asarray(window)
        #blink = np.sum(np.abs(awindow[0:N/2]))

        plotter.plotdata( [eeg, 0, 0, blink])
        #plotter.plotdata( [eeg, 0, 0])
        samples = (np.sin(2*np.pi*np.arange(fs*duration)*(fwave+int(eeg))/fs)).astype(np.float32)
        stream.write(volume*samples)

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S.%f')
        f.write( str(ts) + ' ' + str(count) + ' ' + str(eeg) + ' ' + str(attention) + ' ' + str(meditation) + ' ' + str(blink) + '\n')
finally:
    headset.stop()
    f.close()
     
asignaleeg = np.asarray( signaleeg )
meanval = np.mean( signaleeg )
stdval = np.std( signaleeg )

print(meanval)
print(stdval)
print("Press a key")
sys.stdin.read(1)