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
    config["global"] = {}
    config["global"]["client_id"] = client_id
    config["global"]["secret"] = secret
    config["global"]["redirect_uri"] = redirect_uri
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w') as conf:
        config.write(conf)

def player_control(key, player, args):
    if(key == 5): # Alt+Return
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


# main starts here

# initialize config parser
config = ConfigParser()
config_file = os.path.join(os.path.expanduser("~"), ".config/rofi-spotify/config")
config.read(config_file)

# initialize argument parser
parser = argparse.ArgumentParser(description='Rofi frontend for simple spotify control')
parser.add_argument('--setup', action='store_true', help='Setup your config file')
parser.add_argument('--set-default-device', action='store_true', help='Select your default device')
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
elif args.set_default_device: # when --set-default-device is present
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
    if len(devices) == 0: 
        r.error("No device found where music could get played on")
        exit(0)
    device = devices[0]
    r.status("Loading playlists...")
    playlists = user.get_all_playlists()
    r.close()

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

    playlist_index, playlist_key = r.select('Playlist', options, message=msg, key5=('Alt+Return', "Play/Pause"), key6=('Alt+Left', "Previous"), key7=('Alt+Right', "Next"), rofi_args=['-i'])

    if(playlist_key == 0): # Enter from playlist selection
        r.status("Loading songs...")
        songs = playlists[playlist_index].get_all_tracks()
        r.close()
        options = ["Shuffle"]
        for s in songs:
            options.append(s.name + " - " + s.artist.name)
        song_index, song_key = r.select('Song', options, message=msg, key5=('Alt+Return', "Play/Pause"), key6=('Alt+Left', "Previous"), key7=('Alt+Right', "Next"), rofi_args=['-i'])
        
        if(song_key == 0): # Enter from song selection
            if(song_index == 0): # Shuffle Option selected
                player.play(playlists[playlist_index], device=device)
                player.shuffle(state=True, device=device)
                player.set_repeat(state="context", device=device)
                player.next(device=device)
                if not args.no_notify: notify_song(user)
            else:
                player.play(playlists[playlist_index], offset=song_index-1, device=device)
                if not args.no_notify: notify_song(user)
        else:
            player_control(song_key, player, args)
         
    else:
        player_control(playlist_key, player, args)
