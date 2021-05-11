# A python script to do both listening and talking. This is the basic model
# for an audio-only mumble client.

# Usage:

# Install pyaudio (instructions: https://people.csail.mit.edu/hubert/pyaudio/#downloads)
# If `fatal error: 'portaudio.h' file not found` is encountered while installing
# pyaudio even after following the instruction, this solution might be of help:
# https://stackoverflow.com/questions/33513522/when-installing-pyaudio-pip-cannot-find-portaudio-h-in-usr-local-include
#
# Install dependencies for pymumble.
#
# Set up a mumber server. For testing purpose, you can use https://guildbit.com/
# to spin up a free server. Hard code the server details in this file.
#
# run `python3 ./listen_n_talk.py`. Now an audio-only mumble client is connected
# to the server.
#
# To test its functionality, in a separate device, use some official mumble
# client (https://www.mumble.com/mumble-download.php) to verbally communicate
# with this audio-only client.
#
# Works on MacOS. Does NOT work on RPi 3B+ (I cannot figure out why. Help will
# be much appreciated)

#import pymumble.pymumble_py3 as pymumble_py3
import os
import pymumble_py3
from pymumble_py3.callbacks import PYMUMBLE_CLBK_SOUNDRECEIVED as PCS
import pyaudio

# Connection details for mumble server. Hardcoded for now, will have to be
# command line arguments eventually
pwd = "1337"  # password
server = "pascalpieper.de"  # server address
nick = str(os.getlogin()) + "-bot"
port = 64738  # port number

print("using bot name: " + nick)

# pyaudio set up
CHUNK = 1024
FORMAT = pyaudio.paInt16  # pymumble soundchunk.pcm is 16 bits
RATE = 48000  # pymumble soundchunk.pcm is 48000Hz

p = pyaudio.PyAudio()


info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
numUsableDevices = 0
for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print ("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'), "(" +
            str(p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) +" channels )")
            numUsableDevices += 1


device = int(input("pls choose a device: (0-" + str(numUsableDevices-1) + ") "))
print("k, using " + p.get_device_info_by_host_api_device_index(0, device).get('name'))
CHANNELS = max(p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels'), 2)

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,  # talk
                output=True,  # and listen
                frames_per_buffer=CHUNK,
                input_device_index=device)


# mumble client set up
def sound_received_handler(user, soundchunk):
    """ play sound received from mumble server upon its arrival """
    stream.write(soundchunk.pcm)


# Spin up a client and connect to mumble server
mumble = pymumble_py3.Mumble(server, nick, password=pwd, port=port,
            stereo = CHANNELS == 2)
# set up callback called when PCS event occurs
mumble.callbacks.set_callback(PCS, sound_received_handler)
#mumble.set_receive_sound(1)  # Enable receiving sound from mumble server
mumble.start()
mumble.is_ready()  # Wait for client is ready


# constant capturing sound and sending it to mumble server
while True:
    data = stream.read(CHUNK, exception_on_overflow=False)
    mumble.sound_output.add_sound(data)


# close the stream and pyaudio instance
stream.stop_stream()
stream.close()
p.terminate()
