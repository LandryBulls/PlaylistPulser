"""
light_control.py

Description: This script provides all the lighting control. It is responsible for controlling the DMX lights and RGB lights, loading profiles, 
setting up the DMX controller, providing functions for sending signals to the DMX controller, and providing functions for controlling the RGB lights.

Author: Landry Bulls
Date: 8/20/24
"""

import pandas as pd
import sounddevice as sd
from PyDMXControl.controllers import OpenDMXController
from PyDMXControl.profiles.Generic import Dimmer, Custom
import threading
import queue
import os
import json
from mapping import fft_to_rgb, power_to_brightness

def load_json(json_file):
    with open(json_file, 'r') as f:
        loaded = json.load(f)
    return loaded

def load_profile(profile_name):
    with open(f'profiles/{profile_name}.json', 'r') as f:
        profile = json.load(f)
    return profile

def load_controller(profile):
    controller = OpenDMXController()
    for light in profile['lights']:
        if light['type'] == 'dimmer':
            controller.add_fixture(Dimmer(name=light['name']))
        elif light['type'] == 'custom':
            controller.add_light(Custom(name=light['name'], n_channels=light['channels']))
    return controller

class SceneManager:
    def __init__(self, scenes_directory, profile_name):
        self.scenes = self.load_json_files(scenes_directory)
        self.current_scene = None

    def load_json_files(self, directory):
        data = {}
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                with open(os.path.join(directory, filename), 'r') as file:
                    data[filename[:-5]] = json.load(file)
        return data

    def set_scene(self, scene_name):
        if scene_name in self.scenes:
            self.current_scene = self.scenes[scene_name]
        else:
            raise ValueError(f"Scene '{scene_name}' not found")

class LightController(threading.Thread):
    def __init__(self, audio_listener, profile_name, scene_manager):
        threading.Thread.__init__(self)
        self.audio_listener = audio_listener
        self.profile = load_profile(profile_name)
        self.dmx_controller = load_controller(self.profile)
        self.scene_manager = scene_manager
        self.running = threading.Event()

    def run(self):
        self.running.set()
        while self.running.is_set():
            fft_data = self.audio_listener.get_fft_data(timeout=0.1)
            if fft_data is not None:
                dmx_values = self.process_fft(fft_data)
                self.dmx_controller.set_channels(dmx_values) # will need to interrogate this further. not sure what to pass to set_channels. 
            
            self.check_scene_updates()

    def process_fft(self, fft_data):
        dmx_values = {}
        scene = self.scene_manager.current_scene

        for light in scene['lights']:
            if light['name'] in self.profile['lights']:
                profile_light = next(l for l in self.profile['lights'] if l['name'] == light['name'])
                light_dmx = self.calculate_light_dmx(light, profile_light, fft_data)
                dmx_values.update(light_dmx)

        return dmx_values

    def calculate_light_dmx(self, scene_light, profile_light, fft_data):
        # use self.dmx_controller.get_fixtures_by_name(scene_light['name']) to get the fixture object
        pass


    def stop(self):
        self.running.clear()

def main():
    audio_listener = AudioListener()

    initial_scene = load_json('default_scene.json')  # Load your initial scene
    
    light_controller = LightController(audio_listener, dmx_controller, initial_scene)
    
    audio_listener.start()
    light_controller.start()

    try:
        while True:
            # Main program logic
            # Maybe handle user input to change scenes
            pass
    finally:
        audio_listener.stop()
        light_controller.stop()
        audio_listener.join()
        light_controller.join()

if __name__ == "__main__":
    main()






