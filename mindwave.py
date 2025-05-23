'''
Mindwave Mobile Serial Driver for Python 3.x

This driver implements the serial protocol that is being used in the Mindwave Mobile Headset.

 OfflineHeadset: this class can be used in the same as Headset to replay a previous stored file.

'''
from __future__ import print_function

import select, serial, threading
from pprint import pprint
import time
import datetime
import os

# Byte codes
CONNECT              = b'\xc0'
DISCONNECT           = b'\xc1'
AUTOCONNECT          = b'\xc2'
SYNC                 = b'\xaa'
EXCODE               = 0x55
POOR_SIGNAL          = 0x02
ATTENTION            = 0x04
MEDITATION           = 0x05
BLINK                = 0x16
HEADSET_CONNECTED    = b'\xd0'
HEADSET_NOT_FOUND    = b'\xd1'
HEADSET_DISCONNECTED = b'\xd2'
REQUEST_DENIED       = b'\xd3'
STANDBY_SCAN         = b'\xd4'
RAW_VALUE            = 0x80
ASIC_EEG_POWER       = b'\x83'

# Status codes
STATUS_CONNECTED     = 'connected'
STATUS_SCANNING      = 'scanning'
STATUS_STANDBY       = 'standby'

# Use me to playback previous recorded files as if they were recorded now.
# (using the same python class)
class OfflineHeadset:
    """
    An Offline MindWave Headset
    """
    def __init__(self, filename):
        self.basefilename = filename
        self.readcounter = 0
        self.running = True
        self.fileindex = 0
        self.f = None
        self.poor_signal = 1
        self.count = 0

    def setup(self):
        pass

    def setupfile(self):
        self.datasetfile = self.basefilename
        print(self.datasetfile)
        if os.path.isfile(self.datasetfile):
            if self.f:
                self.f.close()
            self.f = open(self.datasetfile,'r')
            return True
        else:
            return False

    def nextline(self):
        line = None
        if self.f:
            line = self.f.readline()
        if (not line):
            self.fileindex = self.fileindex + 1

            if self.setupfile():
                return self.nextline()
            else:
                return None
        else:
            return line

    def dequeue(self):
        line = self.nextline()
        if (line):
            data = line.split('\r\n')[0].split(' ')
            self.raw_value = data[1]
            self.attention = data[2]
            self.meditation = data[3]
            self.blink = data[4]

            self.readcounter = self.readcounter + 1
            self.count = self.count
            return self
        else:
            self.running = False
            return None


    def close(self):
        if (self.f):
            self.f.close()

    def stop(self):
        self.close()


class Headset(object):
    """
    A MindWave Headset
    """

    class DongleListener(threading.Thread):
        """
        Serial listener for dongle device.
        """
        def __init__(self, headset, *args, **kwargs):
            """Set up the listener device."""
            self.headset = headset
            self.counter = 0
            super(Headset.DongleListener, self).__init__(*args, **kwargs)

        def run(self):
            """Run the listener thread."""
            s = self.headset.dongle
            self.headset.running = True

            # Re-apply settings to ensure packet stream
            try:
                s.write(DISCONNECT)
                d = s.getSettingsDict()
                for i in range(2):
                    d['rtscts'] = not d['rtscts']
                    s.applySettingsDict(d)
            except Exception as e:
                print(f"Error inicializando dongle: {e}")
                self.headset.running = False
                return

            while self.headset.running:
                try:
                    if s.read() == SYNC and s.read() == SYNC:
                        # Packet found, determine plength
                        while True:
                            plength = ord(s.read())
                            if plength != 170:
                                break
                        if plength > 170:
                            continue

                        # Read in the payload
                        payload = s.read(plength)

                        # Verify its checksum
                        val = sum(b for b in payload[:-1])
                        val &= 0xff
                        val = ~val & 0xff
                        chksum = ord(s.read())

                        #if val == chksum:
                        if True: # ignore bad checksums
                            self.parse_payload(payload)
                except (select.error, OSError, serial.SerialException) as e:
                    print(f"Error en la lectura del dongle: {e}")
                    break
                except Exception as e:
                    print(f"Error inesperado: {e}")
                    break

            print('Closing connection...')
            if s and s.isOpen():
                try:
                    s.close()
                except Exception:
                    pass

        def parse_payload(self, payload):
            """Parse the payload to determine an action."""
            while payload:
                # Parse data row
                excode = 0
                try:
                    code, payload = payload[0], payload[1:]
                    self.headset.count = self.counter
                    self.counter = self.counter + 1
                    if (self.counter >= 100):
                        self.counter = 0
                except IndexError:
                    pass
                while code == EXCODE:
                    # Count excode bytes
                    excode += 1
                    try:
                        code, payload = payload[0], payload[1:]
                    except IndexError:
                        pass
                if code < 0x80:
                    # This is a single-byte code
                    try:
                        value, payload = payload[0], payload[1:]
                    except IndexError:
                        pass
                    if code == POOR_SIGNAL:
                        # Poor signal
                        old_poor_signal = self.headset.poor_signal
                        self.headset.poor_signal = value
                        if self.headset.poor_signal > 0:
                            if old_poor_signal == 0:
                                for handler in \
                                    self.headset.poor_signal_handlers:
                                    handler(self.headset,
                                            self.headset.poor_signal)
                        else:
                            if old_poor_signal > 0:
                                for handler in \
                                    self.headset.good_signal_handlers:
                                    handler(self.headset,
                                            self.headset.poor_signal)
                    elif code == ATTENTION:
                        # Attention level
                        self.headset.attention = value
                        for handler in self.headset.attention_handlers:
                            handler(self.headset, self.headset.attention)
                    elif code == MEDITATION:
                        # Meditation level
                        self.headset.meditation = value
                        for handler in self.headset.meditation_handlers:
                            handler(self.headset, self.headset.meditation)
                    elif code == BLINK:
                        # Blink strength
                        self.headset.blink = value
                        for handler in self.headset.blink_handlers:
                            handler(self.headset, self.headset.blink)
                else:
                    # This is a multi-byte code
                    try:
                        vlength, payload = payload[0], payload[1:]
                    except IndexError:
                        continue
                    value, payload = payload[:vlength], payload[vlength:]

                    # FIX: accessing value crashes elseway
                    if code == RAW_VALUE and len(value) >= 2:
                        raw=value[0]*256+value[1]
                        if (raw>=32768):
                            raw=raw-65536
                        self.headset.raw_value = raw
                        for handler in self.headset.raw_value_handlers:
                            handler(self.headset, self.headset.raw_value)
                    if code == HEADSET_CONNECTED:
                        # Headset connect success
                        run_handlers = self.headset.status != STATUS_CONNECTED
                        self.headset.status = STATUS_CONNECTED
                        self.headset.headset_id = value.encode('hex')
                        if run_handlers:
                            for handler in \
                                self.headset.headset_connected_handlers:
                                handler(self.headset)
                    elif code == HEADSET_NOT_FOUND:
                        # Headset not found
                        if vlength > 0:
                            not_found_id = value.encode('hex')
                            for handler in \
                                self.headset.headset_notfound_handlers:
                                handler(self.headset, not_found_id)
                        else:
                            for handler in \
                                self.headset.headset_notfound_handlers:
                                handler(self.headset, None)
                    elif code == HEADSET_DISCONNECTED:
                        # Headset disconnected
                        headset_id = value.encode('hex')
                        for handler in \
                            self.headset.headset_disconnected_handlers:
                            handler(self.headset, headset_id)
                    elif code == REQUEST_DENIED:
                        # Request denied
                        for handler in self.headset.request_denied_handlers:
                            handler(self.headset)
                    elif code == STANDBY_SCAN:
                        # Standby/Scan mode
                        try:
                            byte = ord(value[0])
                        except IndexError:
                            byte = None
                        if byte:
                            run_handlers = (self.headset.status !=
                                            STATUS_SCANNING)
                            self.headset.status = STATUS_SCANNING
                            if run_handlers:
                                for handler in self.headset.scanning_handlers:
                                    handler(self.headset)
                        else:
                            run_handlers = (self.headset.status !=
                                            STATUS_STANDBY)
                            self.headset.status = STATUS_STANDBY
                            if run_handlers:
                                for handler in self.headset.standby_handlers:
                                    handler(self.headset)
                    elif code == ASIC_EEG_POWER:
                        j = 0
                        for i in ['delta', 'theta', 'low-alpha', 'high-alpha', 'low-beta', 'high-beta', 'low-gamma', 'mid-gamma']:
                            self.headset.waves[i] = ord(value[j])*255*255+ord(value[j+1])*255+ord(value[j+2])
                            j += 3
                        for handler in self.headset.waves_handlers:
                            handler(self.headset, self.headset.waves)

    def __init__(self, device, headset_id=None, open_serial=True):
        """Initialize the  headset."""
        # Initialize headset values
        self.dongle = None
        self.listener = None
        self.device = device
        self.headset_id = headset_id
        self.poor_signal = 255
        self.attention = 0
        self.meditation = 0
        self.blink = 0
        self.raw_value = 0
        self.waves = {}
        self.status = None
        self.count = 0
        self.running = False
        self._log_callback = None  # Callback externo para logs/notificaciones

        # Create event handler lists
        self.poor_signal_handlers = []
        self.good_signal_handlers = []
        self.attention_handlers = []
        self.meditation_handlers = []
        self.blink_handlers = []
        self.raw_value_handlers = []
        self.waves_handlers = []
        self.headset_connected_handlers = []
        self.headset_notfound_handlers = []
        self.headset_disconnected_handlers = []
        self.request_denied_handlers = []
        self.scanning_handlers = []
        self.standby_handlers = []

        # Open the socket
        if open_serial:
            self.serial_open()

    def set_log_callback(self, callback):
        """Permite registrar un callback para logs/notificaciones externas."""
        self._log_callback = callback

    def _log(self, msg):
        if self._log_callback:
            self._log_callback(msg)
        else:
            print(msg)

    def connect(self, headset_id=None):
        """Connect to the specified headset id."""
        try:
            if headset_id:
                self.headset_id = headset_id
            else:
                headset_id = self.headset_id
                if not headset_id:
                    self.autoconnect()
                    return
            self.dongle.write(''.join([CONNECT, headset_id.decode('hex')]))
        except Exception as e:
            self._log(f"Error al conectar: {e}")

    def autoconnect(self):
        """Automatically connect device to headset."""
        try:
            self.dongle.write(AUTOCONNECT)
        except Exception as e:
            self._log(f"Error en autoconnect: {e}")

    def disconnect(self):
        """Disconnect the device from the headset."""
        try:
            self.dongle.write(DISCONNECT)
        except Exception as e:
            self._log(f"Error al desconectar: {e}")

    def serial_open(self):
        """Open the serial connection and begin listening for data."""
        try:
            if not self.dongle or not self.dongle.isOpen():
                self.dongle = serial.Serial(self.device, 115200)
            if not self.listener or not self.listener.isAlive():
                self.listener = self.DongleListener(self)
                self.listener.daemon = True
                self.listener.start()
        except Exception as e:
            self._log(f"Error abriendo el puerto serie: {e}")

    def serial_close(self):
        """Close the serial connection."""
        try:
            self.dongle.close()
        except Exception as e:
            self._log(f"Error cerrando el puerto serie: {e}")

    def stop(self):
        self.running = False
        try:
            if self.listener and self.listener.is_alive():
                self.listener.join(timeout=1)
        except Exception:
            pass
        try:
            self.serial_close()
        except Exception:
            pass
