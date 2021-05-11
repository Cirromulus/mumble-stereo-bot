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
import os
import pymumble_py3
from pymumble_py3.callbacks import PYMUMBLE_CLBK_SOUNDRECEIVED as PCS
import pyaudio
import configparser

# Todo: parse input
configname_for_server = "DEFAULT_SERVER"

config = configparser.ConfigParser()
config_filename = 'config.ini'

config.read(config_filename)

# Config individually for server
if not configname_for_server in config:
    config[configname_for_server] = {}
if not config[configname_for_server].get('servername'):
    config[configname_for_server]['servername'] = input("servername: ")
if not config[configname_for_server].get('password'):
    config[configname_for_server]['password'] = input("password: ")
if not config[configname_for_server].get('port'):
    config[configname_for_server]['port'] = input("Port (enter to accept default 64738): ") or "64738"  
if not config[configname_for_server].get('botname'):
    config[configname_for_server]['botname'] = str(os.getlogin()) + "-bot"
if not config[configname_for_server].get('channel'):
    config[configname_for_server]['channel'] = str(0)
    
# user-dependent config 
if not os.getlogin() in config: 
    config[os.getlogin()] = {}

server = config[configname_for_server]['servername']
pwd = config[configname_for_server]['password']
port = int(config[configname_for_server]['port'])
nick = config[configname_for_server].get('botname', str(os.getlogin()) + "-bot")

# pyaudio set up
CHUNK = config[os.getlogin()].getint('chunks', 1024)
FORMAT = pyaudio.paInt16  # pymumble soundchunk.pcm is 16 bits
RATE = config[os.getlogin()].getint('samplerate', 48000)  # pymumble soundchunk.pcm is 48000Hz

target_device = config[os.getlogin()].get('usb_device', 'ask')
found_device_id = None

p = pyaudio.PyAudio()
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')

# first, "silent" loop
for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            d_name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            if target_device == d_name:
                found_device_id = i

if found_device_id is None:
    # Present devices to user
    print("Did not find configured device '" + target_device + "'")
    maxdevices = 0
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            d_name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            print ("Input Device id ", i, " - ", d_name, "(" +
                str(p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) +" channels )")
            maxdevices = max(maxdevices, i)
    found_device_id = int(input("pls choose a device: (0-" + str(maxdevices) + ") "))
    
found_device_name = p.get_device_info_by_host_api_device_index(0, found_device_id).get('name')
print("using '" + found_device_name + "'")
config[os.getlogin()]['usb_device'] = found_device_name

#prepare stream
CHANNELS = max(p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels'), 2)
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,  # talk
                output=True,  # and listen
                frames_per_buffer=CHUNK,
                input_device_index=found_device_id)


# mumble client set up
def sound_received_handler(user, soundchunk):
    """ play sound received from mumble server upon its arrival """
    stream.write(soundchunk.pcm)


# Spin up a client and connect to mumble server
print("Connecting to " + server)
mumble = pymumble_py3.Mumble(server, nick, password=pwd, port=port,
            stereo = CHANNELS == 2)
# set up callback called when PCS event occurs
mumble.callbacks.set_callback(PCS, sound_received_handler)
#mumble.set_receive_sound(1)  # Enable receiving sound from mumble server
mumble.start()
mumble.is_ready()  # Wait for client is ready

target_channel = mumble.channels[int(config[configname_for_server]['channel'])]
if target_channel is not None:
    print("Moving into remembered channel '" + target_channel['name'] + "'")
    target_channel.move_in()
else:
    print("Channel ID " + config[configname_for_server]['channel'] + " not found")




print("Connected. Running...")
# constant capturing sound and sending it to mumble server
try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        mumble.sound_output.add_sound(data)

except KeyboardInterrupt:
    pass


print("Saving current channel '" + mumble.channels[mumble.users.myself['channel_id']]['name'] + "'")
config[configname_for_server]['channel'] = str(mumble.users.myself['channel_id'])

# Save config
with open(config_filename, 'w') as configfile:
    config.write(configfile)

print("Exit")
# close the stream and pyaudio instance
stream.stop_stream()
stream.close()
p.terminate()
