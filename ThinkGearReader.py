#coding: latin-1
# Run me with frameworkpython inside a virtual environment.

# This program connect to ThinkGear and receives via TCP/IP all the
# raw streaming from NeuroSky MindWave Mobile (the black headset)
# It also plot the signal using matplotlib.

import socket
import json

import matplotlib.pyplot as plt

import time, datetime

ip = '127.0.0.1'
port = 13854

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (ip,port)
sock.connect(server_address)

# Send to ThinkGear the command to start receiving packages.
msg = "{\"enableRawOutput\": true, \"format\": \"JSON\"}"
sent = sock.sendto(msg, server_address)


# Make the socket to be crlf aware.
myfile = sock.makefile()
data = myfile.readline()

import Plotter
plotter = Plotter(500,-500,500)

attention = 0
meditation = 0
eeg = 0

ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S')
f = open('eeg.'+st+'.dat', 'w')

try:
    while (True):
        data = myfile.readline()

        print (data)

        obj = json.loads(data)

        if "rawEeg" in obj:
            eeg = obj["rawEeg"]

        if "eSense" in obj:
            attention = obj["eSense"]["attention"]
            meditation = obj["eSense"]["meditation"]

        f.write( str(eeg) + ' ' + str(attention) + ' ' + str(meditation) + '\n')

        plotter.plotdata( [eeg, attention, meditation])
finally:
    sock.close()
