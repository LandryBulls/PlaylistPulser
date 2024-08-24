#!/usr/bin/env python
# coding: utf-8

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

import os
import pandas as pd
import numpy as np
from pathlib import Path
import time
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor

import ipywidgets as widgets
from savify import Savify
from savify.types import Type, Format, Quality
from savify.utils import PathHolder
import logging

from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from scipy.cluster.hierarchy import dendrogram
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.neighbors import NearestNeighbors

from tqdm import tqdm
from IPython.display import display
import plotly.graph_objects as go
import plotly.subplots

from PyDMXControl.controllers import OpenDMXController
from PyDMXControl.profiles.Generic import Dimmer, Custom

import sounddevice as sd
from tqdm import tqdm
import threading
import matplotlib.pyplot as plt
import threading
import pickle

get_ipython().run_line_magic('matplotlib', 'inline')

# get the client id and client secret from the text file
with open('spotify_credentials.txt') as f:
    client_id = f.readline().strip().split(' ')[1]
    client_secret = f.readline().strip().split(' ')[1]
    uri = f.readline().split(' ')[1][:-1]

uri = 'http://localhost:8000'

# set the environment variables
os.environ['SPOTIPY_CLIENT_ID'], os.environ['SPOTIFY_CLIENT_ID'] = client_id, client_id
os.environ['SPOTIPY_CLIENT_SECRET'], os.environ['SPOTIFY_CLIENT_SECRET'] = client_secret, client_secret
os.environ['SPOTIPY_REDIRECT_URI'], os.environ['SPOTIFY_REDIRECT_URI'] = uri, uri

#sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

auth_manager = SpotifyClientCredentials()
sp = spotipy.Spotify(auth_manager=auth_manager)

# just add all the scopes
scopes = ['user-library-read',
            'user-read-recently-played',
            'user-top-read',
            'user-follow-read',
            'user-read-playback-position',
            'user-read-playback-state',
            'user-read-currently-playing',
            'user-modify-playback-state',
            'user-read-private',
            'playlist-read-private',
            'playlist-read-collaborative',
            'playlist-modify-public',
            'playlist-modify-private']

username = '1260351083'

token = spotipy.util.prompt_for_user_token(username, scopes)

if token:
    sp = spotipy.Spotify(auth=token)
    saved_tracks_resp = sp.current_user_saved_tracks(limit=50)
else:
    print('Couldn\'t get token for that username')

path_holder = PathHolder(downloads_path='downloads')
logger = logging.getLogger('savify')
s = Savify(path_holder=path_holder, logger=logger, download_format=Format.MP3)

user = sp.user(username)
sp.user = user


# make a dict of RGB colors to their DMX values
# this is the color wheel
colors = {
    'red': [255, 0, 0],
    'orange': [255, 127, 0],
    'yellow': [255, 255, 0],
    'green': [0, 255, 0],
    'blue': [0, 0, 255],
    'purple': [75, 0, 130],
    'pink': [255, 0, 255],
    'white': [255, 255, 255]
}

def RGB(brightness=255, color='pink', strobe=False, strobe_speed=0):
    """
    Returns the list of 7 DMX values for the RGB light
    """
    if strobe:
        strobe_val = 255
    else:
        strobe_val = 0
    return [brightness, colors[color][0], colors[color][1], colors[color][2], strobe_speed, 0, 0]

def get_bass_brightness(bass_power):
    return int(MIN_BASS_BRIGHTNESS + (bass_power - BASS_MIN_THRESHOLD) * (BASS_BRIGHTNESS_RANGE / BASS_POWER_RANGE))


with open("elm_cluster.pkl", "rb") as f:
    model = pickle.load(f)


def get_playlist_df(playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    # convert this into a dataframe with the audio features, song name, artist, id, and link
    features = []
    for track in tracks:
        feature_data = sp.audio_features(track['track']['id'])[0]
        feature_data['name'] = track['track']['name']
        feature_data['artist'] = track['track']['artists'][0]['name']
        feature_data['id'] = track['track']['id']
        feature_data['link'] = track['track']['external_urls']['spotify']
        feature_data['popularity'] = track['track']['popularity']
        feature_data['genres'] = sp.artist(track['track']['artists'][0]['id'])['genres']
        feature_data['cluster'] = None
        feature_data['scene'] = None
        features.append(feature_data)

    out = pd.DataFrame(features)
    # drop "type" and "uri" columns
    out.drop(columns=['type', 'uri'], inplace=True)
    return out


elm_tracks = get_playlist_df('spotify:playlist:1nNxmkhYsOpa6Ux9MFJLoc')


# just make a function that makes a function (nested func) and then give that output to the callback
# so it would be like with sd.InputStream(callback=light_sound(scene_dict), device=3, channels=16, samplerate=16000, blocksize=blocksize)

def scene(scene_dict_template):
    """
    Takes a scene dict, sets the lights to the init parameters, and returns a callback function to give to the 
    light controller thread.

    scene_dict is a dictionary that has the following keys:
    'BASS_RANGE': a list of two integers that are the start and end of the bass range
    'BASS_MAX': the maximum bass power that will be reached
    'BASS_MAX_THRESHOLD': the bass power that will trigger the scene
    'BASS_MIN_THRESHOLD': the bass power that will trigger the scene
    'MIN_BASS_BRIGHTNESS': the minimum brightness that will be reached
    'MAX_BASS_BRIGHTNESS': the maximum brightness that will be reached
    'BASS_MAP': the light that bass controls
    'HIGH_RANGE': a list of two integers that are the start and end of the high hat range
    'HIGH_THRESH': the high hat power that will trigger the scene
    'HIGH_MAP': the light that high hat controls (usually strobe)
    'STROBE_ENABLED': a boolean that determines whether the strobe will be enabled
    'STROBE_SPEED': the speed of the strobe
    'DISCOBALL_ENABLED': a boolean that determines whether the discoball lights will be enabled
    'LASERS_ENABLED': a boolean that determines whether the lasers will be enabled
    'LAMP_ENABLED': a boolean that determines whether the lamp will be enabled
    'RGB_ENABLED': a boolean that determines whether the RGB lights will be enabled
    'RGB_MAP': a list of integers that map the RGB lights to the frequency bins
    'RGB_MAX': the maximum brightness of the RGB lights
    'RGB_MIN': the minimum brightness of the RGB lights
    'RGB_THRESH': the threshold for the RGB lights
    'RGB_MODE': the mode of the RGB lights (0 is monochrome, 1 is reactive)
    'RGB_COLOR': the color of the RGB lights (if monochrome)
    'RGB_STROBE_TRIGGER': the threshold for the RGB lights to strobe
    'RGB_STROBE_SPEED': the speed of the RGB lights when they strobe
    'RGB_STROBE_INTENSITY': the intensity of the RGB lights when they strobe
    'RGB_STROBE_ENABLED': a boolean that determines whether the RGB lights will strobe
    'RGB_STROBE_MODE': the mode of the RGB lights when they strobe (0 is monochrome, 1 is reactive)
    """
    scene_dict = scene_dict_template.copy()
    # first update all the lights to match the scene
        self.profile['ropes'].dim(scene_dict['MIN_BASS_BRIGHTNESS'])
        if scene_dict['DISCOBALL_ENABLED']:
            self.profile['discoball'].dim(255)
        else:
            self.profile['discoball'].dim(0)
        if scene_dict['LASERS_ENABLED']:
            self.profile['lasers'].dim(255)
        else:
            self.profile['lasers'].dim(0)
        if scene_dict['LAMP_ENABLED']:
            self.profile['lamp'].dim(255)
        else:
            self.profile['lamp'].dim(0)

        # get the rgb keys that exist in self.profile
        rgb_lights = []
        for key in self.profile.keys():
            if 'rgb' in key:
                rgb_lights.append(self.profile[key])

        
        # init strobe to 0 always
        self.profile['strobe_intensity'].dim(0)
        self.profile['strobe_speed'].dim(0)

        if scene_dict['RGB_ENABLED']:
            if scene_dict['RGB_MODE'] == 0:
                for i in rgb_lights:
                    i.set_channels(RGB(brightness=scene_dict['RGB_MAX'], color=scene_dict['RGB_COLOR']))
            elif scene_dict['RGB_MODE'] == 1:
                # do the reactive thing
                # (just set to dim pink for now)
                for i in rgb_lights:
                    i.set_channels(RGB(brightness=scene_dict['RGB_MAX'], color='pink'))
        else:
            for i in rgb_lights:
                i.set_channels(RGB(brightness=0))


        def get_dmx_value(bass_power, scene_dict):
            BASS_BRIGHTNESS_RANGE = scene_dict['MAX_BASS_BRIGHTNESS'] - scene_dict['MIN_BASS_BRIGHTNESS']
            BASS_POWER_RANGE = scene_dict['BASS_MAX_THRESHOLD'] - scene_dict['BASS_MIN_THRESHOLD']
            dmx_value = int(scene_dict['MIN_BASS_BRIGHTNESS'] + (bass_power - scene_dict['BASS_MIN_THRESHOLD']) * (BASS_BRIGHTNESS_RANGE / BASS_POWER_RANGE))
            return dmx_value

        def get_bass_brightness(bass_power):
            return int(scene_dict['MIN_BASS_BRIGHTNESS'] + (bass_power - scene_dict['BASS_MIN_THRESHOLD']) * (BASS_BRIGHTNESS_RANGE / BASS_POWER_RANGE))

        # turn all the frequency bins into indices
        scene_dict['BASS_RANGE'] = [freq_to_index(scene_dict['BASS_RANGE'][0]), freq_to_index(scene_dict['BASS_RANGE'][1])]
        scene_dict['HIGH_RANGE'] = [freq_to_index(scene_dict['HIGH_RANGE'][0]), freq_to_index(scene_dict['HIGH_RANGE'][1])]
        scene_dict['RGB_STROBE_TRIGGER'] = freq_to_index(scene_dict['RGB_STROBE_TRIGGER'])
        # check if anything is mapped to the strobe:
        strobe_maps = []
        for par, val in scene_dict.items():
            if self.profile['strobe_intensity'] == val:
                strobe_maps.append(par)
        if not scene_dict['STROBE_ENABLED'] and (len(strobe_maps) > 0):
            print('Warning: strobe is not enabled but is mapped to a parameter. Strobe will not be enabled.')
            for par in strobe_maps:
                scene_dict[par] = null

        # turn lasers on or off
        if scene_dict['LASERS_ENABLED']:
            self.profile['lasers'].dim(255)
        else:
            self.profile['lasers'].dim(0)
        

        # now do the callback
        def out_scene(indata, outdata, frames, time, status=None):
            power_spectrum = np.abs(np.fft.rfft(np.sum(indata, axis=1), n=None))
            power_specs.append(power_spectrum.tolist())

            # get the average power in the bass range
            bass_power = np.mean(power_spectrum[scene_dict['BASS_RANGE'][0]:scene_dict['BASS_RANGE'][1]])

            # get the average power in the mid range
            mid_power = np.mean(power_spectrum[scene_dict['MID_RANGE'][0]:scene_dict['MID_RANGE'][1]])

            # get the average power in the high hat range
            high_hat_power = np.mean(power_spectrum[scene_dict['HIGH_RANGE'][0]:scene_dict['HIGH_RANGE'][1]])
            
            # get the total power
            total_power = np.sum(power_spectrum)

            # set the bass light
            if bass_power > scene_dict['BASS_MAX']:
                scene_dict['BASS_MAP'].dim(scene_dict['MAX_BASS_BRIGHTNESS'])
            elif bass_power < scene_dict['BASS_MIN_THRESHOLD']:
                scene_dict['BASS_MAP'].dim(scene_dict['MIN_BASS_BRIGHTNESS'])
            else:
                # map between min bass brightness and max bass brightness
                scene_dict['BASS_MAP'].dim(get_dmx_value(bass_power, scene_dict))

            # set the high hat light
            if high_hat_power > scene_dict['HIGH_THRESH']:
                scene_dict['HIGH_MAP'].dim(255)
            elif high_hat_power < scene_dict['HIGH_THRESH']:
                scene_dict['HIGH_MAP'].dim(0)

            # set the RGB lights
            if scene_dict['RGB_ENABLED']:
                if scene_dict['RGB_MODE'] == 1:
                    # reactive
                    if total_power > scene_dict['RGB_THRESH']:
                        for i in rgb_lights:
                            i.set_channels(RGB(brightness=scene_dict['RGB_MAX'], color='pink'))
                    else:
                        for i in rgb_lights:
                            i.set_channels(RGB(brightness=scene_dict['RGB_MIN'], color='pink'))

            # set the strobe
            if scene_dict['STROBE_ENABLED']:
                if high_hat_power > scene_dict['HIGH_THRESH']:
                    self.profile['strobe_intensity'].dim(255)
                    self.profile['strobe_speed'].dim(255)
                elif high_hat_power < scene_dict['HIGH_THRESH']:
                    self.profile['strobe_intensity'].dim(0)
                    self.profile['strobe_speed'].dim(0)

            # map mids to lasers
            if scene_dict['LASERS_ENABLED']:
                if bass_power > scene_dict['BASS_MAX_THRESHOLD']-10:
                    self.profile['lasers'].dim(255)
                elif bass_power < scene_dict['BASS_MAX_THRESHOLD']-10:
                    self.profile['lasers'].dim(0)

        return out_scene






class Pulser(object):
    def __init__(self):
        self._running = False
        self.last_song = None
        self.df = pd.read_csv('elm_tracks.csv')
        self.scene_controller = None
        self.dmx = OpenDMXController()
        self.SAMPLERATE = 16000
        self.MINIMUM_FREQUENCY = 20
        self.BLOCKSIZE = int(round(self.SAMPLERATE/self.MINIMUM_FREQUENCY))
        self.model = model
        # get the black hole
        audio_devices = sd.query_devices()
        for device in audio_devices:
            if device['name'] == 'BlackHole 16ch':
                self.device_index = device['index']

        # add the lighting profile
        self.profile = {}
        self.profile['ropes'] = self.dmx.add_fixture(Dimmer)
        self.profile['discoball'] = self.dmx.add_fixture(Dimmer)
        self.profile['lasers'] = self.dmx.add_fixture(Dimmer)
        self.profile['lamp'] = self.dmx.add_fixture(Dimmer)
        self.profile['strobe_speed'] = self.dmx.add_fixture(Dimmer)
        self.profile['strobe_intensity'] = self.dmx.add_fixture(Dimmer)

        for i in range(1, 9):
            self.profile['rgb'+str(i)] = self.dmx.add_fixture(Custom(channels=7, start_channel=7*i))
        null = self.dmx.add_fixture(Dimmer) 

        self.scene_mappings = {
            0 : self.warm,
            1 : self.hiphop,
            2 : self.dubstep,
            3 : self.goosebumps
            4 : self.hiphop,
            5 : self.hiphop
        }

        self.SCENE_TEMPLATE = {
            'BASS_RANGE': [20, 500], # frequency range for bass
            'BASS_MAX': 35, # maximum bass power
            'BASS_MAX_THRESHOLD': 20, # bass power that will trigger the scene
            'BASS_MIN_THRESHOLD': 2, # bass power that will trigger the scene
            'MIN_BASS_BRIGHTNESS': 0, # minimum brightness that will be reached
            'MAX_BASS_BRIGHTNESS': 75, # maximum brightness that will be reached
            'BASS_MAP': self.profile['ropes'], # light that bass controls
            'MID_RANGE': [350, 2000], # frequency range for mid
            'MID_THRESH': 0.03, # mid power that will trigger the scene
            'HIGH_RANGE': [2000, 16000], # frequency range for high hat
            'HIGH_THRESH': 1, # high hat power that will trigger the scene
            'HIGH_MAP': self.profile['strobe_intensity'], # light that high hat controls (usually strobe)
            'STROBE_ENABLED': True, # whether the strobe will be enabled
            'STROBE_SPEED': 255, # speed of the strobe
            'DISCOBALL_ENABLED': True, # whether the discoball lights will be enabled
            'LASERS_ENABLED': True, # whether the lasers will be enabled
            'LAMP_ENABLED': True, # whether the lamp will be enabled
            'RGB_ENABLED': True, # whether the RGB lights will be enabled
            'RGB_MAX': 255, # maximum brightness of the RGB lights
            'RGB_MIN': 0, # minimum brightness of the RGB lights
            'RGB_THRESH': 1, # threshold for the RGB lights
            'RGB_MODE': 0, # mode of the RGB lights (0 is monochrome, 1 is reactive)
            'RGB_COLOR': 'pink', # color of the RGB lights (if monochrome)
            'RGB_STROBE_TRIGGER': 1, # threshold for the RGB lights to strobe
            'RGB_STROBE_SPEED': 255, # speed of the RGB lights when they strobe
            'RGB_STROBE_INTENSITY': 255, # intensity of the RGB lights when they strobe
            'RGB_STROBE_ENABLED': False, # whether the RGB lights will strobe
            'RGB_STROBE_MODE': 0 # mode of the RGB lights when they strobe (0 is monochrome, 1 is reactive)
        }

        # warm (for nice acoustic songs)
        self.warm = self.SCENE_TEMPLATE.copy()
        self.warm['RGB_ENABLED'] = False
        self.warm['STROBE_ENABLED'] = False
        self.warm['BASS_RANGE'] = [20, 1000]
        self.warm['MIN_BASS_BRIGHTNESS'] = 50
        self.warm['MAX_BASS_BRIGHTNESS'] = 255
        self.warm['BASS_MAX_THRESHOLD'] = 25
        self.warm['LASERS_ENABLED'] = False
        self.warm['DISCOBALL_ENABLED'] = False

        # hip-hop
        self.hiphop = self.SCENE_TEMPLATE.copy()
        self.hiphop['BASS_RANGE'] = [20, 500]
        self.hiphop['DISCOBALL_ENABLED'] = False
        self.hiphop['LAMP_ENABLED'] = False
        self.hiphop['BASS_MAX_THRESHOLD'] = 15
        self.hiphop['MAX_BASS_BRIGHTNESS'] = 100
        self.hiphop['MIN_BASS_BRIGHTNESS'] = 0
        self.hiphop['HIGH_THRESH'] = 1
        self.hiphop['RGB_COLOR'] = 'red'


        # dubstep
        self.dubstep = self.SCENE_TEMPLATE.copy()
        self.dubstep['BASS_RANGE'] = [20, 200]
        self.dubstep['BASS_MAX'] = 100
        self.dubstep['BASS_MAX_THRESHOLD'] = 50
        self.dubstep['BASS_MIN_THRESHOLD'] = 5
        self.dubstep['MIN_BASS_BRIGHTNESS'] = 20
        self.dubstep['MAX_BASS_BRIGHTNESS'] = 100
        self.dubstep['RGB_ENABLED'] = True
        self.dubstep['RGB_MODE'] = 1
        self.dubstep['RGB_THRESH'] = 1
        self.dubstep['RGB_COLOR'] = 'blue'
        self.dubstep['RGB_STROBE_ENABLED'] = True
        self.dubstep['RGB_STROBE_MODE'] = 1
        self.dubstep['RGB_STROBE_TRIGGER'] = 1
        self.dubstep['RGB_STROBE_SPEED'] = 255
        self.dubstep['RGB_STROBE_INTENSITY'] = 255
        self.dubstep['STROBE_ENABLED'] = True
        self.dubstep['STROBE_SPEED'] = 255
        self.dubstep['DISCOBALL_ENABLED'] = False
        self.dubstep['LAMP_ENABLED'] = False

        # goosebumps
        self.goosebumps = self.SCENE_TEMPLATE.copy()
        self.goosebumps['RGB_MODE'] = 0
        self.goosebumps['RGB_COLOR'] = 'green'
        self.goosebumps['MIN_BASS_BRIGHTNESS'], self.goosebumps['MAX_BASS_BRIGHTNESS'] = 0, 0
        self.goosebumps['LASERS_ENABLED'] = True
        self.goosebumps['DISCOBALL_ENABLED'] = False
        self.goosebumps['BASS_MAP'] = self.profile['rgb1']

        # add scenes as attributes
        self.scenes = {
            'warm': self.warm,
            'hiphop': self.hiphop,
            'dubstep': self.dubstep,
            'goosebumps': self.goosebumps
        }

    def scene(self, scene_dict_template):
        """
        Takes a scene dict, sets the lights to the init parameters, and returns a callback function to give to the 
        light controller thread.

        scene_dict is a dictionary that has the following keys:
        'BASS_RANGE': a list of two integers that are the start and end of the bass range
        'BASS_MAX': the maximum bass power that will be reached
        'BASS_MAX_THRESHOLD': the bass power that will trigger the scene
        'BASS_MIN_THRESHOLD': the bass power that will trigger the scene
        'MIN_BASS_BRIGHTNESS': the minimum brightness that will be reached
        'MAX_BASS_BRIGHTNESS': the maximum brightness that will be reached
        'BASS_MAP': the light that bass controls
        'HIGH_RANGE': a list of two integers that are the start and end of the high hat range
        'HIGH_THRESH': the high hat power that will trigger the scene
        'HIGH_MAP': the light that high hat controls (usually strobe)
        'STROBE_ENABLED': a boolean that determines whether the strobe will be enabled
        'STROBE_SPEED': the speed of the strobe
        'DISCOBALL_ENABLED': a boolean that determines whether the discoball lights will be enabled
        'LASERS_ENABLED': a boolean that determines whether the lasers will be enabled
        'LAMP_ENABLED': a boolean that determines whether the lamp will be enabled
        'RGB_ENABLED': a boolean that determines whether the RGB lights will be enabled
        'RGB_MAP': a list of integers that map the RGB lights to the frequency bins
        'RGB_MAX': the maximum brightness of the RGB lights
        'RGB_MIN': the minimum brightness of the RGB lights
        'RGB_THRESH': the threshold for the RGB lights
        'RGB_MODE': the mode of the RGB lights (0 is monochrome, 1 is reactive)
        'RGB_COLOR': the color of the RGB lights (if monochrome)
        'RGB_STROBE_TRIGGER': the threshold for the RGB lights to strobe
        'RGB_STROBE_SPEED': the speed of the RGB lights when they strobe
        'RGB_STROBE_INTENSITY': the intensity of the RGB lights when they strobe
        'RGB_STROBE_ENABLED': a boolean that determines whether the RGB lights will strobe
        'RGB_STROBE_MODE': the mode of the RGB lights when they strobe (0 is monochrome, 1 is reactive)
        """
        scene_dict = scene_dict_template.copy()
        # first update all the lights to match the scene
        self.profile['ropes'].dim(scene_dict['MIN_BASS_BRIGHTNESS'])
        if scene_dict['DISCOBALL_ENABLED']:
            self.profile['discoball'].dim(255)
        else:
            self.profile['discoball'].dim(0)
        if scene_dict['LASERS_ENABLED']:
            self.profile['lasers'].dim(255)
        else:
            self.profile['lasers'].dim(0)
        if scene_dict['LAMP_ENABLED']:
            self.profile['lamp'].dim(255)
        else:
            self.profile['lamp'].dim(0)

        # get the rgb keys that exist in self.profile
        rgb_lights = []
        for key in self.profile.keys():
            if 'rgb' in key:
                rgb_lights.append(self.profile[key])
            
        # init strobe to 0 always
        self.profile['strobe_intensity'].dim(0)
        self.profile['strobe_speed'].dim(0)

        if scene_dict['RGB_ENABLED']:
            if scene_dict['RGB_MODE'] == 0:
                for i in rgb_lights:
                    i.set_channels(RGB(brightness=scene_dict['RGB_MAX'], color=scene_dict['RGB_COLOR']))
            elif scene_dict['RGB_MODE'] == 1:
                # do the reactive thing
                # (just set to dim pink for now)
                for i in rgb_lights:
                    i.set_channels(RGB(brightness=scene_dict['RGB_MAX'], color='pink'))
        else:
            for i in rgb_lights:
                i.set_channels(RGB(brightness=0))


        def get_dmx_value(bass_power, scene_dict):
            BASS_BRIGHTNESS_RANGE = scene_dict['MAX_BASS_BRIGHTNESS'] - scene_dict['MIN_BASS_BRIGHTNESS']
            BASS_POWER_RANGE = scene_dict['BASS_MAX_THRESHOLD'] - scene_dict['BASS_MIN_THRESHOLD']
            dmx_value = int(scene_dict['MIN_BASS_BRIGHTNESS'] + (bass_power - scene_dict['BASS_MIN_THRESHOLD']) * (BASS_BRIGHTNESS_RANGE / BASS_POWER_RANGE))
            return dmx_value

        def get_bass_brightness(bass_power):
            return int(scene_dict['MIN_BASS_BRIGHTNESS'] + (bass_power - scene_dict['BASS_MIN_THRESHOLD']) * (BASS_BRIGHTNESS_RANGE / BASS_POWER_RANGE))

        # turn all the frequency bins into indices
        scene_dict['BASS_RANGE'] = [freq_to_index(scene_dict['BASS_RANGE'][0]), freq_to_index(scene_dict['BASS_RANGE'][1])]
        scene_dict['HIGH_RANGE'] = [freq_to_index(scene_dict['HIGH_RANGE'][0]), freq_to_index(scene_dict['HIGH_RANGE'][1])]
        scene_dict['RGB_STROBE_TRIGGER'] = freq_to_index(scene_dict['RGB_STROBE_TRIGGER'])
        # check if anything is mapped to the strobe:
        strobe_maps = []
        for par, val in scene_dict.items():
            if self.profile['strobe_intensity'] == val:
                strobe_maps.append(par)
        if not scene_dict['STROBE_ENABLED'] and (len(strobe_maps) > 0):
            print('Warning: strobe is not enabled but is mapped to a parameter. Strobe will not be enabled.')
            for par in strobe_maps:
                scene_dict[par] = null

        # turn lasers on or off
        if scene_dict['LASERS_ENABLED']:
            self.profile['lasers'].dim(255)
        else:
            self.profile['lasers'].dim(0)
            

        # now do the callback
        def out_scene(indata, outdata, frames, time, status=None):
            power_spectrum = np.abs(np.fft.rfft(np.sum(indata, axis=1), n=None))
            power_specs.append(power_spectrum.tolist())
            # get the average power in the bass range
            bass_power = np.mean(power_spectrum[scene_dict['BASS_RANGE'][0]:scene_dict['BASS_RANGE'][1]])
            # get the average power in the mid range
            mid_power = np.mean(power_spectrum[scene_dict['MID_RANGE'][0]:scene_dict['MID_RANGE'][1]])
            # get the average power in the high hat range
            high_hat_power = np.mean(power_spectrum[scene_dict['HIGH_RANGE'][0]:scene_dict['HIGH_RANGE'][1]])
            # get the total power
            total_power = np.sum(power_spectrum)

            # set the bass light
            if bass_power > scene_dict['BASS_MAX']:
                scene_dict['BASS_MAP'].dim(scene_dict['MAX_BASS_BRIGHTNESS'])
            elif bass_power < scene_dict['BASS_MIN_THRESHOLD']:
                scene_dict['BASS_MAP'].dim(scene_dict['MIN_BASS_BRIGHTNESS'])
            else:
                # map between min bass brightness and max bass brightness
                scene_dict['BASS_MAP'].dim(get_dmx_value(bass_power, scene_dict))

            # set the high hat light
            if high_hat_power > scene_dict['HIGH_THRESH']:
                scene_dict['HIGH_MAP'].dim(255)
            elif high_hat_power < scene_dict['HIGH_THRESH']:
                scene_dict['HIGH_MAP'].dim(0)

            # set the RGB lights
            if scene_dict['RGB_ENABLED']:
                if scene_dict['RGB_MODE'] == 1:
                    # reactive
                    if total_power > scene_dict['RGB_THRESH']:
                        for i in rgb_lights:
                            i.set_channels(RGB(brightness=scene_dict['RGB_MAX'], color='pink'))
                    else:
                        for i in rgb_lights:
                            i.set_channels(RGB(brightness=scene_dict['RGB_MIN'], color='pink'))

            # set the strobe
            if scene_dict['STROBE_ENABLED']:
                if high_hat_power > scene_dict['HIGH_THRESH']:
                    self.profile['strobe_intensity'].dim(255)
                    self.profile['strobe_speed'].dim(255)
                elif high_hat_power < scene_dict['HIGH_THRESH']:
                    self.profile['strobe_intensity'].dim(0)
                    self.profile['strobe_speed'].dim(0)

            # map mids to lasers
            if scene_dict['LASERS_ENABLED']:
                if bass_power > scene_dict['BASS_MAX_THRESHOLD']-10:
                    self.profile['lasers'].dim(255)
                elif bass_power < scene_dict['BASS_MAX_THRESHOLD']-10:
                    self.profile['lasers'].dim(0)

        return out_scene

    def start(self):
        self._running = True
        self.current_song = self.get_current_song()
        self.cur_genre = sp.artist(sp.track(self.current_song)['artists'][0]['id'])['genres'][0]
        # check if song is in the dataframe
        if self.current_song in self.df['id'].values:
            self.last_song = self.current_song
            self.current_scene = self.df[self.df['id'] == self.current_song]['scene'].values[0]
            self.pulse()
        else:
            # get the artists of the current song
            current_artists = sp.track(self.current_song)['artists']
            # get the genres of the artists
            genres = []
            for artist in current_artists:
                genres.extend(sp.artist(artist['id'])['genres'])
            # convert genre list to single string with commas
            genres = ', '.join(genres)
            # get the cluster by embedding and fitting
            cluster = self.model.predict(self.model.embed([genres]))[0]
            # get the scene associated with each cluster

    def get_current_song(self):
        self.current_song = sp.current_user_playing_track()['item']['id']

    def run_scene(self, scene_dict):
        scene = self.scene(scene_dict)
        with sd.InputStream(callback=scene, device=self.device_index, channels=1, samplerate=16000, blocksize=self.BLOCKSIZE):
            while True:
                continue

    def pulse(self):
        # start a run_scene thread
        self.scene_thread = threading.Thread(target=self.run_scene, args=(self.current_scene))
        self.scene_thread.start()

    def start_scene(self):
        # start the scene thread
        self.scene_thread = threading.Thread(target=self.run)
    
    def get_scene(self, song_id):
        # check if song is in the dataframe
        if song_id in self.df['id'].values:
            return self.df[self.df['id'] == song_id]['scene'].values[0]
        else:
            # estimate the scene based on genre
    
    def terminate(self):
        self._running = False
    
    def run(self):
        while self._running:
            current_song = self.get_current_song()
            if current_song != self.last_song:
                self.last_song = current_song
                self.pulse()
            time.sleep(1)


