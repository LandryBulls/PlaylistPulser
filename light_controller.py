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

def load_json(json_file):
    with open(json_file, 'r') as f:
        loaded = json.load(f)
    return loaded

def load_profile(profile):
    controller = OpenDMXController()
    for light in profile['lights']:
        if light['type'] == 'dimmer':
            controller.add_fixture(Dimmer(name=light['name']))
        elif light['type'] == 'custom':
            controller.add_light(Custom(name=light['name'], n_channels=light['channels']))
    return controller

def fft_to_dmx(fft_data, scene_mapping):
    # Apply mapping to fft_data
    # Return DMX values as a dict of light identities and values
    pass

class LightController(threading.Thread):
    def __init__(self, audio_listener, dmx_controller, initial_scene, profile):
        threading.Thread.__init__(self)
        self.audio_listener = audio_listener
        self.dmx_controller = dmx_controller
        self.current_scene = initial_scene
        self.running = threading.Event()
        self.scene_queue = queue.Queue()

    def run(self):
        self.running.set()
        while self.running.is_set():
            fft_data = self.audio_listener.get_fft_data(timeout=0.1)
            if fft_data is not None:
                dmx_values = self.process_fft(fft_data)
                self.dmx_controller.set_channels(dmx_values)
            
            self.check_scene_updates()

    def process_fft(self, fft_data):
        # Apply current scene's mapping to fft_data
        # Return DMX values as a dict of light identities and values
        pass

    def change_scene(self, new_scene):
        self.scene_queue.put(new_scene)

    def check_scene_updates(self):
        try:
            new_scene = self.scene_queue.get_nowait()
            self.current_scene = new_scene
        except queue.Empty:
            pass

    def stop(self):
        self.running.clear()

# Usage
def main():
    audio_listener = AudioListener()
    dmx_controller = OpenDMxController()  # Initialize your PyDMX controller
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






