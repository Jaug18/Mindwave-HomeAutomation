import mindwave, time
from pprint import pprint

headset = mindwave.Headset('/dev/tty.MindWaveMobile-DevA','ef47')
time.sleep(2)

attention = 0
meditation = 0
eeg = 0


def on_raw( headset, rawvalue):
    (count,eeg, attention, meditation, blink) = (headset.count, headset.raw_value, headset.attention, headset.meditation, headset.blink)
    print("Count %d :Raw value: %s, Attention: %s, Meditation: %s, Blink: %s" % (headset.count, headset.raw_value, headset.attention, headset.meditation, headset.blink))


try:
    while (headset.poor_signal > 5):
        print("Headset signal noisy %d. Adjust the headset and the earclip." % (headset.poor_signal))
        time.sleep(0.01)

    headset.raw_value_handlers.append( on_raw )
        
    print("Reading data...")
    while (True):
        pass

finally:
    headset.stop()