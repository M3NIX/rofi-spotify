# rofi-spotify

A simple playlist picker for spotify with rofi as frontend

## Installing

`pip install python-rofi notify-send spotify --user`

## Setup 

1. Go to the [Spotify dashboard](https://developer.spotify.com/dashboard/applications)
1. Click `Create a Client ID` and create an app
1. Now click `Edit Settings`
1. Add `http://localhost:8080/callback` to the Redirect URIs
1. You are now ready to authenticate with Spotify!
1. Go back to the terminal
1. Run `./rofi-spotify.py --setup`
1. Enter your `Client ID`
1. Enter your `Client Secret`
1. Enter your `Redirect URI`
1. You will be redirected to an official Spotify webpage to ask you for permissions.
1. Enter the localhost url from the browser
1. Ready to use :)

Your config will be stored under `~/.config/rofi-spotify/config`

## Usage

Create a keybinding which launches the script without any parameters.
To be able to play song you will need a running spotify client (e.g. [spotifyd](https://github.com/Spotifyd/spotifyd))

By default:
- the playlist will start with shuffling turned on
- the script will give notifications (with notify-send) when starting a playlist/song
- choose the first available active spotify device 

To disable this default behaviour you can use the flags `--no-shuffle` and `--no-notify`.
To select a default device which should get used (when available) run the script once with `--default-device`. 

# Keyboard shortcuts

|  Shortcut |     Action    |
|:---------:|:-------------:|
| Alt+Enter |   Play/Pause  |
|  Alt+Left | Previous Song |
| Alt+Right |   Next Song   |  
