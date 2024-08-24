"""
interface.py

Description: This script provides a command line interface for toggling light mappings and controlling the Spotify API.

Key Classes/Functions:
TBD

Author: Landry Bulls
Date: 8/20/24
"""

import sys
import os
import keyboard
import itertools
from time import sleep
from threading import Thread
import sounddevice as sd
from scipy.io import wavfile
import numpy as np

# Global variables
global beep_status
beep_status = True
global beepsound
beepsound = (np.sin(2*np.pi*1500*np.linspace(0, 2, int(44100*0.1))) + np.sin(2*np.pi*3*np.linspace(0, 2, int(44100*0.1))))*np.linspace(0, 1, int(44100*0.1))
def print_colored(text, color, end='\n'):
    colors = {'red': '\x1b[31m', 'green': '\x1b[32m', 'yellow': '\x1b[33m', 'blue': '\x1b[34m'}
    reset = '\x1b[0m'
    sys.stdout.write(colors.get(color, '') + text + reset + end)

# #from .light_control import Pulser, scenes
# from . import spotifizer

# def change_scene(key):
#     global current_scene
#     if key.name in scenes.keys():
#         current_scene = key.name
#         print(f"{current_scene} mode activated")

# def toggle_lights():
#     global current_scene
#     if current_scene == "start":
#         # Turn on the lights
#         None

# event_dict = {
#     "enter": toggle_lights,
#     "q": sys.exit,
# }

# keyboard.on_press(change_scene)

# pulser = Pulser()

### Aesthetic ASCII Art ###
oculizer_title = """
      ___           ___           ___           ___                   ___           ___           ___     
     /\  \         /\  \         /\__\         /\__\      ___        /\  \         /\  \         /\  \    
    /::\  \       /::\  \       /:/  /        /:/  /     /\  \       \:\  \       /::\  \       /::\  \   
   /:/\:\  \     /:/\:\  \     /:/  /        /:/  /      \:\  \       \:\  \     /:/\:\  \     /:/\:\  \  
  /:/  \:\  \   /:/  \:\  \   /:/  /  ___   /:/  /       /::\__\       \:\  \   /::\~\:\  \   /::\~\:\  \ 
 /:/__/ \:\__\ /:/__/ \:\__\ /:/__/  /\__\ /:/__/     __/:/\/__/ _______\:\__\ /:/\:\ \:\__\ /:/\:\ \:\__\ 
 \:\  \ /:/  / \:\  \  \/__/ \:\  \ /:/  / \:\  \    /\/:/  /    \::::::::/__/ \:\~\:\ \/__/ \/_|::\/:/  /
  \:\  /:/  /   \:\  \        \:\  /:/  /   \:\  \   \::/__/      \:\~~\~~      \:\ \:\__\      |:|::/  / 
   \:\/:/  /     \:\  \        \:\/:/  /     \:\  \   \:\__\       \:\  \        \:\ \/__/      |:|\/__/  
    \::/  /       \:\__\        \::/  /       \:\__\   \/__/        \:\__\        \:\__\        |:|  |    
     \/__/         \/__/         \/__/         \/__/                 \/__/         \/__/         \|__|    
"""
def beep(freq=1500, duration=0.1, volume=0.5):
    if beep_status:
        sd.play(beepsound, 44100, blocking=False)

# flush the print buffer
print('\n'*100)
beep()
sleep(0.05)
print_colored(oculizer_title, 'green')
print_colored("Welcome to Oculizer! Press enter to turn on the lights. Hold 'q' to quit. Press a state key then enter to change the light mapping.", 'blue')

if __name__ == "__main__":
    while True:
        try:
            if keyboard.is_pressed("q"):
                break
            else:
                pass
            event = keyboard.read_event()
            print(event.name, end='\r')  # Use '\r' to overwrite the previous printed text
        except KeyboardInterrupt:
            break


