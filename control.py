"""
light_control.py

Description: This script provides all the lighting control. It is responsible for controlling the DMX lights and RGB lights, loading profiles, 
setting up the DMX controller, providing functions for sending signals to the DMX controller, and providing functions for controlling the RGB lights.

Author: Landry Bulls
Date: 8/20/24
"""

from PyDMXControl.controllers import OpenDMXController
from PyDMXControl.profiles.Generic import Dimmer, Custom
from custom_profiles.RGB import RGB
from custom_profiles.ADJ_strobe import Strobe
import threading
import queue
import os
import json
from mapping import fft_to_rgb, fft_to_strobe, fft_to_dimmer, generate_RGB_signal, bool_rgb
from audio_listener import AudioListener
from scene_manager import SceneManager
from utils import load_json 

def load_profile(profile_name):
    with open(f'profiles/{profile_name}.json', 'r') as f:
        profile = json.load(f)
    return profile

def load_controller(profile):
    controller = OpenDMXController()
    control_dict = {}
    curr_channel = 1
    for light in profile['lights']:
        if light['type'] == 'dimmer':
            control_dict[light['name']] = controller.add_fixture(Dimmer(name=light['name'], start_channel=curr_channel))
            curr_channel += 1
        elif light['type'] == 'rgb':
            control_dict[light['name']] = controller.add_fixture(RGB(name=light['name'], start_channel=curr_channel))
            curr_channel += 6
        elif light['type'] == 'strobe':
            control_dict[light['name']] = controller.add_fixture(Strobe(name=light['name'], start_channel=curr_channel))
            curr_channel += 2

    return controller, control_dict

class LightController(threading.Thread):
    def __init__(self, audio_listener, profile_name, scene_manager):
        threading.Thread.__init__(self)
        self.audio_listener = audio_listener
        self.profile = load_profile(profile_name)
        self.light_names = [i['name'] for i in self.profile['lights']]
        self.dmx_controller, self.controller_dict = load_controller(self.profile)
        self.scene_manager = scene_manager
        self.running = threading.Event()
        self.fft_data = None

    def change_scene(self, scene_name):
        self.scene_manager.set_scene(scene_name)

    def run(self):
        self.running.set()
        while self.running.is_set():
            if self.scene_manager.current_scene['type'] == 'dynamic':
                if not self.audio_listener.fft_queue.empty():
                    try:
                        self.send_dynamic()
                    except Exception as e:
                        print(f"Error sending dynamic data: {str(e)}")
            else:
                self.send_static()
            
    def send_dynamic(self):
        # sends the dmx values to the controller based on the scene mapping
        for light in self.profile['lights']:
            if light['name'] not in self.scene_manager.current_scene['lights']:
                # turn it off
                if light['type'] == 'dimmer':
                    self.controller_dict[light['name']].dim(0)
                elif light['type'] == 'rgb':
                    self.controller_dict[light['name']].set_channels([0,0,0,0,0,0])
                elif light['type'] == 'strobe':
                    self.controller_dict[light['name']].set_channels([0,0])

            elif light['modulator'] == 'fft':
                fft_data = self.audio_listener.fft_queue.get(timeout=0.1)
                if light['type'] == 'dimmer':
                    dmx_value = fft_to_dimmer(fft_data, light['frequency_range'], light['power_range'], light['brightness_range'])
                    self.controller_dict[light['name']].dim(dmx_value)
                elif light['type'] == 'rgb':
                    dmx_values = fft_to_rgb(fft_data, frange=light['frequency_range'], prange=light['power_range'], brange=light['brightness_range'], color=light['color'], strobe=light['strobe'])
                    self.controller_dict[light['name']].set_channels(dmx_values)
                elif light['type'] == 'strobe':
                    dmx_values = fft_to_strobe(fft_data, light['frequency_range'], light['power_range'][0])
                    self.controller_dict[light['name']].set_channels(dmx_values)

            elif light['modulator'] == 'bool':
                if light['type'] == 'dimmer':
                    self.controller_dict[light['name']].dim(light['brightness'])
                elif light['type'] == 'rgb':
                    self.controller_dict[light['name']].set_channels(bool_rgb(light['brightness'], light['color'], light['strobe']))
                elif light['type'] == 'strobe':
                    dmx_values = [light['speed'], light['brightness']]
                    self.controller_dict[light['name']].set_channels(dmx_values)

            elif light['modulator'] == 'time':
                if light['type'] == 'dimmer':
                    self.controller_dict[light['name']].dim(time_dimmer(light))
    
    def send_static(self):
        for light in self.scene_manager.current_scene['lights']:
            if light['name'] not in self.profile['lights']:
                continue
            if light['type'] == 'dimmer':
                self.controller_dict[light['name']].dim(light['brightness'])
            elif light['type'] == 'rgb':
                dmx_values = generate_RGB_signal(brightness=light['brightness'], color=light['color'], strobe=light['strobe'])
                self.controller_dict[light['name']].set_channels(dmx_values)
            elif light['type'] == 'strobe':
                dmx_values = [light['speed'], light['brightness']]
                self.controller_dict[light['name']].set_channels(dmx_values)

    def stop(self):
        self.running.clear()

def main():
    audio_listener = AudioListener()  # Make sure this is imported or defined
    scene_manager = SceneManager('scenes_directory')
    light_controller = LightController(audio_listener, 'default', scene_manager)
    
    audio_listener.start()
    light_controller.start()

    try:
        while True:
            # Add logic here to handle user input for scene changes
            pass
    finally:
        audio_listener.stop()
        light_controller.stop()
        audio_listener.join()
        light_controller.join()

if __name__ == "__main__":
    main()






