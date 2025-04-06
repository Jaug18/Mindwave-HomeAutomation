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

import numpy as np
import cv2
import sys
import time
import datetime

# Python3 implementation of the approach 
from math import sqrt 

# Function to find the circle on 
# which the given three points lie 
def findCircle(x1, y1, x2, y2, x3, y3): 
    x12 = x1 - x2
    x13 = x1 - x3

    y12 = y1 - y2
    y13 = y1 - y3

    y31 = y3 - y1
    y21 = y2 - y1

    x31 = x3 - x1
    x21 = x2 - x1

    # x1^2 - x3^2 
    sx13 = pow(x1, 2) - pow(x3, 2)

    # y1^2 - y3^2 
    sy13 = pow(y1, 2) - pow(y3, 2)

    sx21 = pow(x2, 2) - pow(x1, 2)
    sy21 = pow(y2, 2) - pow(y1, 2)

    if ((y31) * (x12) - (y21) * (x13) == 0):
        f = 1
    else:
        f = (((sx13) * (x12) + (sy13) *
            (x12) + (sx21) * (x13) +
            (sy21) * (x13)) // (2 *
            ((y31) * (x12) - (y21) * (x13))))
            
    if ((x31) * (y12) - (x21) * (y13)==0):
        g = 1
    else:
        g = (((sx13) * (y12) + (sy13) * (y12) +
            (sx21) * (y13) + (sy21) * (y13)) //
            (2 * ((x31) * (y12) - (x21) * (y13))))

    c = (-pow(x1, 2) - pow(y1, 2) -
        2 * g * x1 - 2 * f * y1)

    # eqn of circle be x^2 + y^2 + 2*g*x + 2*f*y + c = 0 
    # where centre is (h = -g, k = -f) and 
    # radius r as r^2 = h^2 + k^2 - c 
    h = -g
    k = -f
    sqr_of_r = h * h + k * k - c

    # r is the radius 
    r = round(sqrt(sqr_of_r), 5)

    print("Centre = (", h, ", ", k, ")")
    print("Radius = ", r)

    return [(h,k),r]

# This code is contributed by Ryuga 


height, width = 200, 200
img = np.zeros((height, width, 3), np.uint8)
img[:, :] = [255, 255, 255]

# Pixel position to draw at
row, col = 100, 100

# # Draw a square with position 20, 100 as the top left corner
# for i in range(row, 30):
#     for j in range(col, 110):
#         img[i, j] = [0, 0, 255]


x1 = row-20 ; y1 = col
x2 = row ; y2 = col-20
x3 = row+20 ; y3 = col
[(row, col),r] = findCircle(x1, y1, x2, y2, x3, y3)

cv2.circle(img,(int(row), int(col)), int(r), (0,255,0), -1)

cv2.imwrite("square_circle_opencv.jpg", img)

try:
    while (headset.poor_signal > 5):
        print("Headset signal noisy %d. Adjust the headset and the earclip." % (headset.poor_signal))

    print("Writing %d seconds output to %s" % (lamdalength,logfilename))
    for i in range(0,samplepoints):
        
        img = np.zeros((height, width, 3), np.uint8)
        img[:, :] = [255, 255, 255]
        
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
        f.write( str(st) + ' ' + str(eeg) + ' ' + str(attention) + ' ' + str(meditation) + ' ' + str(blink) + '\n')

        if (len(window)>3):
            x1 = row-10 ; y1 = window[-3]
            x2 = row ; y2 = window[-2]
            x3 = row+10 ; y3 = window[-1]

        [(rows, cols),r] = findCircle(x1, y1, x2, y2, x3, y3)

        cv2.circle(img,(int(row), int(col)), int(r), (0,255,0), -1)

        cv2.imshow('Video Stream', img)

        key = cv2.waitKey(1) & 0xFF

        # if the `q` key was pressed, break from the loop
        if key == ord('q'):
            break

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
cv2.destroyAllWindows()
