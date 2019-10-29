#!/usr/bin/env python3

from configparser import ConfigParser
from urllib.parse import urlparse
import requests
import webbrowser
import argparse
import time
import json
import os

import spotify.sync as spotify
from notify import Notification
from rofi import Rofi

def notify_song(user):
    time.sleep(.300)
    curr = user.currently_playing()['item']
    Notification(curr.artist.name, title=curr.name)

def authorize(redirect_uri, client_id, secret, grant_type, token_code):
    auth = {}
    payload = {'redirect_uri': redirect_uri, 'client_id': client_id, 'client_secret': secret}
    if grant_type == "authorization_code":
        payload['grant_type'] = 'authorization_code'
        payload['code'] = token_code
    elif grant_type == "refresh_token":
        payload['grant_type'] = 'refresh_token'
        payload['refresh_token'] = token_code
        auth['refresh_token'] = token_code

    result = requests.post("https://accounts.spotify.com/api/token", data=payload)
    response_json = result.json()
    
    # write everything to file
    auth["expires_at"] = time.time() + response_json['expires_in'] - 60
    auth["access_token"] = response_json['access_token']
    if "refresh_token" in response_json:
        auth['refresh_token'] = response_json["refresh_token"]

    config["auth"] = auth
    config["global"]["client_id"] = client_id
    config["global"]["secret"] = secret
    config["global"]["redirect_uri"] = redirect_uri
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w') as conf:
        config.write(conf)

# main starts here

# initialize config parser
config = ConfigParser()
config_file = os.path.join(os.path.expanduser("~"), ".config/rofi-spotify/config")
config.read(config_file)

# initialize argument parser
parser = argparse.ArgumentParser(description='Rofi frontend for simple spotify control')
parser.add_argument('--setup', action='store_true', help='Setup your config file')
parser.add_argument('--default-device', action='store_true', help='Select your default device')
parser.add_argument('--no-shuffle', action='store_true', help='Disable shuffling when starting a playlist')
parser.add_argument('--no-notify', action='store_true', help='Disable the notifications when starting songs')
args = parser.parse_args()

# initialize rofi
r = Rofi()

if args.setup: # when --setup is present
    client_id = input("Client ID: ")
    secret = input("Client Secret: ")
    redirect_uri = input("Callback URL (e.g. http://localhost:8080/callback): ")

    scopes = ('user-modify-playback-state', 'user-read-currently-playing', 'user-read-playback-state', 'playlist-read-private', 'playlist-read-collaborative')
    oauth2 = spotify.OAuth2(client_id, redirect_uri, scopes=scopes)

    # open the browser so the user can authorize to spotify and save the resulting tokens
    webbrowser.open(oauth2.url)
    url = input("Paste localhost url: ")
    parsed_url = urlparse(url)
    code = parsed_url.query.split('=')[1]
    authorize(redirect_uri, client_id, secret, "authorization_code", code)
elif args.default_device: # when --default-device is present
    if 'auth' not in config:
        r.error('Please start the script in the command line with --setup')
        exit(0)
    client = spotify.Client(config['global']['client_id'], config['global']['secret'])
    user = client.user_from_token(config['auth']['access_token'])
    devices = user.get_devices()
    options = []
    for d in devices:
        options.append(d.name)
    index, key = r.select('Spotify Device', options)

    if(key == 0): # Enter
        device = devices[index]
        config["global"]['default_device'] = str(device)
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as conf:
            config.write(conf)

else:
    if 'auth' not in config:
        r.error('Please start the script in the command line with --setup')
        exit(0)

    if time.time() > float(config['auth']['expires_at']):
        authorize(config['global']['redirect_uri'], config['global']['client_id'], config['global']['secret'], "refresh_token", config['auth']['refresh_token'])
        config.read(config_file)

    client = spotify.Client(config['global']['client_id'], config['global']['secret'])
    user = client.user_from_token(config['auth']['access_token'])
    player = user.get_player()
    devices = user.get_devices()
    if len(devices) == 0: r.error("No device found where music could get played on")
    device = devices[0]
    playlists = user.get_all_playlists()
    

    if "default_device" in config["global"]:
        for d in devices:
            if str(d) == config["global"]["default_device"]:
                device = d
    
    options = []
    for p in playlists:
        options.append(p.name)

    msg = "<b>Currently Playing:</b> "
    curr = user.currently_playing()
    if 'item' in curr:
        msg += Rofi.escape(curr['item'].name + " - " + curr['item'].artist.name)

    index, key = r.select('Spotify', options, message=msg, key5=('Alt+Return', "Play/Pause"), key6=('Alt+Left', "Previous"), key7=('Alt+Right', "Next"))

    if(key == 0): # Enter
        player.play(playlists[index], device=device)
        if not args.no_shuffle:
            player.shuffle(state=True, device=device)
            player.next(device=device)
        if not args.no_notify: notify_song(user)
    elif(key == 5): # Alt+Return
        if(player.is_playing):
            player.pause()
        else:
            player.resume()
            if not args.no_notify: notify_song(user)
    elif(key == 6): # Alt-Left
        player.previous()
        player.previous()
        if not args.no_notify: notify_song(user)
    elif(key == 7): # Alt-Right
        player.next()
        if not args.no_notify: notify_song(user)
