#!/usr/bin/env python3

# programme to fetch current radio show and track art, as well as artist and show information for BBC radio streams
# designed to run along side Volumio, as the current BBC streams don't contain useful art or artist and song information

import requests
import os
from PIL import Image
import time
from pytz import timezone
import sys
import datetime as dt
from io import BytesIO
from socketIO_client import SocketIO
import json

# get the path of the script
script_path = os.path.dirname(os.path.abspath(__file__))
# set script path as current directory
os.chdir(script_path)

# set timezone for BBC
tz = timezone('Europe/London')

# output file for show, title and track informtion
outpath = '/data/plugins/system_hardware/pirateaudio/'
outfilename = outpath + 'bbc_radio.json'

# size of BBC art file to fetch
art_size = 240

print('BBC radio art finder - json output to :{0}'.format(outfilename))

# get list of BBC networks, including station names and url information
r=requests.get('https://rms.api.bbc.co.uk/v2/networks')
networks = r.json()
print('Got BBC network information')

# BBC art urls have text to be replaced with appropriate size of returned art
art_url_replace_text = '{recipe}'
art_url_replace_with = str(art_size)+'x'+str(art_size)

# timing, show and track information initialisation
SHOW_END = 0
TRACK_END = 0
LASTUPDATE = 0
NEXTUPDATE = 0
RADIO_STATION = 'undefined'
RADIO_SHOW = ''
RADIO_TRACK = ''
RADIO_ARTIST = ''
status = 'startup'
nowplaying = 'undefined'
time_adjust = 190 # the times quoted for start and end of tracks seems to be out by a constant offset . Add this to current time to make more consistent

# routine to check that the queried URLs returned valid data
def checkbbcreturn(status_code,querystr):
    if status_code == 400:
        print('Request had bad syntax or the parameters supplied were invalid.  Request was [{0}]'.format(querystr))
    elif status_code == 401:
        print('Unauthorized.')
    elif status_code == 403:
        print('Unauthorized. You do not have permission to access this endpoint')
    elif status_code == 404:
        print('Server has not found a route matching the given URI.  Request was [{0}]'.format(querystr))
    elif status_code == 500:
        print('Server encountered an unexpected condition which prevented it from fulfilling the request.  Request was [{0}]'.format(querystr))
    elif status_code == 200:
        return True
    else:
        print('An unexpected return value was provided.  Value was [{0}]. Request was [{1}]'.format(status_code,querystr))
        return False

# default display art to show information - will be overridden if current track information is available
display = 'showinfo'

# track data for output to file for daclcd.py
data = {}
data['album'] = ''
data['title'] = ''
data['artist'] = ''
data['img_url'] = ''
data['valid_until'] = 0

# main routine
while True:

    updateoutput = False

    # query volumio status
    querystr = 'http://localhost:3000/api/v1/getState'
    try:
        r = requests.get(querystr)
        volumio = r.json()
        status = volumio['status']
        service = volumio['service'] # service will be web radio for BBC radio

        volumioartist = ''
        volumiotitle = ''
        uri = ''

        # HLS streams leave artist and title blanks which isn't very helpful, but uri contains station code
        if volumio['artist'] is not None:
            volumioartist = volumio['artist']  # artist will be BBC Radio
        if volumio['title'] is not None:
            volumiotitle = volumio['title'] # title will be e.g. BBC Radio 6 Music
        if volumio['uri'] is not None:
            uri = volumio['uri']

        if status == 'play' and (service == 'webradio' or service == 'mpd') and ((volumioartist == 'BBC Radio') or ('bbc' in uri)):
            playingBBC = True
            # BBC has recently defaulted to just calling the album and track 'BBC Radio', . Some information is in stream URI
            if volumiotitle == 'BBC Radio' or volumioartist == '':
                if 'bbc_radio_one' in uri:
                    volumiotitle = 'BBC Radio 1'
                if 'bbc_radio_two' in uri:
                    volumiotitle = 'BBC Radio 2'
                if 'bbc_radio_three' in uri:
                    volumiotitle = 'BBC Radio 3'
                if 'bbc_radio_fourfm' in uri:
                    volumiotitle = 'BBC Radio 4'
                if 'bbc_radio_five_live' in uri:
                    volumiotitle = 'BBC Radio 5 live'
                if 'bbc_6music' in uri:
                    volumiotitle = 'BBC Radio 6 Music'
            if 'BBC Radio 4' in volumiotitle:
                volumiotitle = 'BBC Radio 4'
            if volumiotitle != RADIO_STATION:    # has station changed? If so, find new station name and network station code
                for x in networks['data']:
                    if volumiotitle == x['long_title']:
                        station_code = x['id']
                        print('\nStation long title: \'{0}\', id: {1}'.format(x['long_title'],x['id']))
                        RADIO_STATION = volumiotitle
                        NEXTUPDATE = 0
        else:
            playingBBC = False
    except:
        print(u'Error getting status from volumio')
        playingBBC = False

    temp = dt.datetime.fromtimestamp(time.time(),tz=tz).strftime('%H:%M:%S')

    if playingBBC == True:
        # output information on show and track end times
        print('\r Time {1}, Show end {2}, Track end {3}, nowplaying={4}'.format(
            temp,dt.datetime.utcfromtimestamp(time.time()).strftime('%H:%M:%S'),
                dt.datetime.utcfromtimestamp(abs(SHOW_END)).strftime('%H:%M:%S'),
                    dt.datetime.utcfromtimestamp(TRACK_END).strftime('%H:%M:%S'),nowplaying),end='')
    else:
        print('\rTime {1}, Not playing BBC                                                  '.format(
            temp,dt.datetime.utcfromtimestamp(time.time()).strftime('%H:%M:%S')),end='')


    # check to see if current time is after show or track end times, in which case we need to update
    if playingBBC == True and (time.time() > NEXTUPDATE):

        successfulBBCinfo = True

        print(' - checking for update',end='')

        # get show info
        querystr = 'https://rms.api.bbc.co.uk/v2/networks/' + station_code + '/playable'
        try:
            r = requests.get(querystr)
        except:
            print(u'Can\'t get show info from BBC (connectivity?)')
            successfulBBCinfo = False

        if checkbbcreturn(r.status_code,querystr):
            try:
                show = r.json()
            except (KeyError, IndexError, ValueError):
                print(u'BBC provided an unexpected format for show info.  Received [{0}]'.format(show))
                successfulBBCinfo = False

        if successfulBBCinfo == True:
            # get trackinfo
            querystr = 'https://rms.api.bbc.co.uk/v2/services/' + show['id'] + '/segments/latest?limit=1'
            try:
                r = requests.get(querystr)
            except:
                print(u'Can\'t get track info from BBC (connectivity?)')
                successfulBBCinfo = False
            # Get music track info
            if checkbbcreturn(r.status_code,querystr):
                try:
                    track = r.json()
                except (KeyError, IndexError, ValueError):
                    print(u'BBC provided an unexpected format for track info.  Received [{0}]'.format(track))
                    successfulBBCinfo = False

        if successfulBBCinfo == True:
            LASTUPDATE = int(time.time())
            # radio show information
            showname = show['titles']['primary']
            # show and track timings
            elapsed = show['progress']['value']
            duration = show['duration']['value']
            # show end should be accurate within a couple of seconds
            SHOW_END = int(time.time()) + duration - elapsed
            #print('\n Show: {0} ({1} of {2})'.format(showname,elapsed,duration)),

            # track information
            if track['data'] != []:      # check track data exists
                trackstart = track['data'][0]['offset']['start']
                trackend = track['data'][0]['offset']['end']
                nowplaying = track['data'][0]['offset']['now_playing']
                # should be accurate within a couple of seconds
                TRACK_END = int(time.time())+ trackend - elapsed
                artist = track['data'][0]['titles']['primary']
                title = track['data'][0]['titles']['secondary']
                album = volumiotitle
                #print(', Track: start {0}, end {1} : {2} by {3}'.format(trackstart,trackend,title,artist))
            else:                      # if no track data
                print('\nQueried {0} and got no track data'.format(querystr))
                trackstart = 0
                trackend = int(time.time()) + 60 # check again in 1 min
                TRACK_END = trackend
                nowplaying = False
                RADIO_TRACK = '<no track info>'
                title = RADIO_TRACK
                RADIO_ARTIST = '<no artist info>'
                artist = RADIO_ARTIST
                album = volumiotitle
                updateoutput = True
                display = 'showinfo'

            if showname != RADIO_SHOW:    # has radio show changed?
                RADIO_SHOW = showname     # if so, change the show name
                show_img_url = show['image_url']
                # image art url has {recipe} in the middle, replace with image dimensions
                show_img_url = show_img_url.replace(art_url_replace_text,art_url_replace_with)
                updateoutput = True

            if RADIO_TRACK != title or RADIO_ARTIST != artist:   # has track changed?
                RADIO_TRACK = title
                RADIO_ARTIST = artist
                track_img_url = track['data'][0]['image_url']
                track_img_url = track_img_url.replace(art_url_replace_text,art_url_replace_with)
                updateoutput = True
                display = 'trackinfo'

            if updateoutput == True:
                print(' - found new show/track',end='')
                print('\n  Show: {0} ({1} of {2})'.format(showname,elapsed,duration),end='')
                print(', Track: start {0}, end {1} : {2} by {3}'.format(trackstart,trackend,title,artist),end='')

        # check track and show info again after track or show ends
        NEXTUPDATE = min(TRACK_END,SHOW_END)

        # elapsed time for show sometimes falls out of sync with track start and end times,
        # if so, fall back on the nowplaying tag
        if (elapsed > trackend):
            if (nowplaying == True):
                NEXTUPDATE = LASTUPDATE+5

        # if track has ended, according to elapsed time of show AND the nowplaying tag is set to False
        # or new show has started, but end time of current track is based upon
        # previous show then switch to showinfo and update in 5s
        if ((elapsed > trackend) and nowplaying == False) or (trackstart > elapsed):
            nowplaying = False
            if display == 'trackinfo':
                display = 'showinfo'
                updateoutput = True
                data['valid_until'] = SHOW_END + 5 # make show data valid until end of show for now
                print(' - track ended',end='')
            NEXTUPDATE = int(time.time()) + 5

        # if playing BBC, but the data hasn't been updated for 60 s then update the output file
        if data['valid_until'] < time.time() + 10:
            updateoutput = True

        #except (KeyError, IndexError, ValueError):
        #    print(u'BBC provided an unexpected response .  Received [{0}]'.format(show))

    else:
        print('                      ',end='')
        album = RADIO_SHOW
        title = RADIO_TRACK
        artist = RADIO_ARTIST
        time.sleep(1)

    if TRACK_END < 0:
        display = 'showinfo'

    # if show or track have changed, update the output
    if updateoutput == True:
        if display == 'trackinfo':
            data['album'] = album
            data['title'] = title
            data['artist'] = artist
            data['img_url'] = track_img_url
        else:
            data['album'] = ''
            data['title'] = showname
            data['artist'] = album
            data['img_url'] = show_img_url
        if data['valid_until'] < NEXTUPDATE + 60:
            data['valid_until'] = NEXTUPDATE + 60 # make this data valid for at least the next 60 seconds, after which display.py will fall back to generic station info
        with open(outfilename, 'w') as outfile:  # output data to json file for display.py to read
            json.dump(data, outfile)
            print(' - updated output file')
        # change the volume to the current value (no change!) to trigger a callback to pirateaudio
        querystr = 'http://localhost:3000/api/v1/commands/?cmd=volume&volume=' + str(volumio['volume'])
        r = requests.get(querystr)
