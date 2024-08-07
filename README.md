# bbcradioart
Service to fetch show and track art for BBC radio streams for Volumio / pirateaudio.

BBC radio is great. Volumio is great. AxLED's Pirateaudio plugin is great.

This is to make all three a bit greater together by fetching the show and artist/song art that the BBC provides via https://rms.api.bbc.co.uk/v2/, as this information is not available in the actual radio stream.

# Requires:

  volumio version 3 on raspberry Pi

  AxLED's pirateaudio plugin (currently has to be installed via https://community.volumio.org/t/plugin-pirate-audio/44336/110?u=arckuk)
  
# Files in this repo:

  display.py
  
    modified version of AxLED's plugin, which contains some minor changes to recognise the output from bbcradioart. copy to /data/plugins/system_hardware/pirateaudio
    
  config.json
  
    modified pirateaudio config file containing a 'rotate' keyword that allows the display to be rotated 180 degrees. copy to /data/configuration/system_hardware/pirateaudio
  
  bbcradioart.py
  
    python program to check status of volumio, and fetch radio station, show and track info then make it available to pirateaudio
  
  bbcradioart.service
  
    service file to start bbcradioart.py automatically at startup 

bbcradioart requires the python timezone pytz and socketIO_client packages:

  sudo pip3 install pytz socketIO_client

check that bbc_radio_art works:

  python3 bbc_radio_art.py
  
# To install this program as a service:
To install this program as a service:

Copy bbc_radio_art.py to a suitable location (/home/volumio is good)

Ensure bbcradioart.service has the correct path to python3 and bbc_radio_art.py: 

nano bbcradioart.service

Copy bbcradioart.service to the systemd folder:

sudo cp bbcradioart.service /etc/systemd/system

Set permissions for the bbcradio.service file :

sudo chmod 644 /etc/systemd/system/bbcradioart.service

Get systemd to recognise the new service:

sudo systemctl daemon-reload

Start the service:

sudo service bbcradioart start

Check the status of the service:

sudo service bbcradioart status

Enable the service so it starts on system boot:

sudo systemctl enable bbcradioart.service
