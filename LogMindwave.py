#coding: latin-1
#
# Connects to the Mindwave using Bluetooth, grabs that raw data as fast as it can
# and dumps everything into a file.
#
# The on_raw function is executed everytime a new raw value is read so it should be
# capturing samples at the effective rate.
#
# Fs = 512

import socket,select
import time, datetime, sys
import matplotlib.pyplot as plt
import sys

lamdalength = 60*1
Fs=512                          # The real output of the device is 512 when used directly.
show=False

# Please provide the number of sample points to take
if (len(sys.argv) > 1):
    samplepoints = int(sys.argv[1])
else:
    samplepoints = Fs*lamdalength

print('Please remove the VGA connection that sometimes interfere with Mindwave')

import mindwave, time
headset = mindwave.Headset('/dev/tty.MindWaveMobile','ef47')

time.sleep(2)

attention = 0
meditation = 0
eeg = 0

ts = time.time()
starttime = 0
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S')
filename = './data/eeg.'+st+'.dat'
f = open(filename, 'w')

def on_raw( headset, rawvalue):
    #time.sleep(.01)
    (count,eeg, attention, meditation, blink) = (headset.count, headset.raw_value, headset.attention, headset.meditation, headset.blink)
    #print("Count %d :Raw value: %s, Attention: %s, Meditation: %s, Blink: %s" % (headset.count, headset.raw_value, headset.attention, headset.meditation, headset.blink))

    ts = time.time()
    f.write( str(ts) + ' ' + str(count) + ' ' + str(eeg) + ' ' + str(attention) + ' ' + str(meditation) + ' ' + str(blink) + '\n')


try:
    while (headset.poor_signal > 5):
        print("Headset signal noisy %d. Adjust the headset and the earclip." % (headset.poor_signal))
        time.sleep(0.01)

    headset.raw_value_handlers.append( on_raw )
        
    print("Writing %d seconds output to %s" % (lamdalength,filename))
    stime = time.time()
    while ((time.time()-stime)<lamdalength):
        time.sleep(.01)
        pass

finally:
    headset.stop()
    f.close()
