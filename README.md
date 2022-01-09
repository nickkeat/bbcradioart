# bbcradioart
Service to fetch show and track art for BBC radio streams for Volumio / pirateaudio.
BBC radio is great. Volumio is great. Pirateaudio plugin is great.

This is to make all three a bit greater together by fetching the show and artist/song art that the BBC provides via https://rms.api.bbc.co.uk/v2/, as this information is not available in the actual radio stream.

Requires:
  volumio version 3
  AxLED's pirateaudio plugin (currently has to be installed via https://community.volumio.org/t/plugin-pirate-audio/44336/110?u=arckuk)
  
Files in this repo:
  display.py
    modified version of AxLED's plugin, which contains some minor changes to recognise the output from bbcradioart
  config.json
    modified pirateaudio config file containing a 'rotate' keyword that allows the display to be rotated 180 degrees
  bbcradioart.py
    python program to check status of volumio, and fetch radio station, show and track info then make it available to pirateaudio
  bbcradioart.service
    service file to start bbcradioart.py automatically at startup
  
To install this program as a service:
Ensure bbcradioart.service has the correct path to python3 and bbcradioart.py: 
  nano bbcradioart.service
Copy bbcradioart.service to the systemd folder:
  sudo cp bbcradioart.service /etc/systemd/system
Set permissions for the bbcradio.service file :
  sudo chmod 644 /etc/systemd/system/bbcradioart.service
Get systemd to recognise the new service:
  sudo systemctl daemon-reload
Reboot the system, or manually get the service to start:
  sudo service bbcradioart start
Check the status of the service:
  sudo service bbcradioart status
