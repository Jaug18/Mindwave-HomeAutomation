import mindwave, time
from pprint import pprint

headset = mindwave.Headset('/dev/tty.MindWaveMobile-DevA','ef47')

time.sleep(2)

# headset.connect()
# print "Connecting..."
#
# while headset.status != 'connected':
#     time.sleep(0.5)
#     if headset.status == 'standby':
#         headset.connect()
#         print "Retrying connect..."
# print "Connected."

def on_raw( headset, rawvalue):
    print( "Count %d :Raw value: %s, Attention: %s, Meditation: %s" % (headset.count, headset.raw_value, headset.attention, headset.meditation))

headset.raw_value_handlers.append( on_raw )


try:
    while (headset.poor_signal > 5):
        print ("Headset signal is too bad %d. Adjust the headset to fit your head." % (headset.poor_signal))

    while (True):
        time.sleep(.01)
        #print "Count %d :Raw value: %s, Attention: %s, Meditation: %s" % (headset.count, headset.raw_value, headset.attention, headset.meditation)
        #pprint(headset.waves)
finally:
    headset.disconnect()
