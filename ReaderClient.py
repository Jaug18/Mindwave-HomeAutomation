#coding: latin-1

import socket, select

import time, datetime, sys

ip = '127.0.0.1'
port = 13855

if (len(sys.argv)>1):
    ip = sys.argv[1]

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (ip,port)
sock.connect(server_address)


ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S')
filename = 'blinking.dat'
f = open(filename, 'w')

# Fire reading.
sent = sock.send('.')

# Make the socket to be crlf aware.
myfile = sock.makefile()


try:
    while (True):
        data = myfile.readline()
        rows = data.split(' ')

        print (data)

        eeg = rows[0]
        attention = rows[1]
        meditation = rows[2]
        counter = rows[3]

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%S.%f')
        f.write( str(st) + ' ' + str(eeg) + ' ' + str(attention) + ' ' + str(meditation) + '\n')
except Exception as e:
    print e

f.close()
sock.close()
