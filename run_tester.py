"""
For testing the functionality of the program.
"""

import os
import json
import threading
import queue
import numpy as np
import curses

from control import load_json, load_profile, load_controller, LightController
from audio_listener import AudioListener
from scene_manager import SceneManager

stdscr = curses.initscr()

def main():
    audio_listener = AudioListener()
    scene_manager = SceneManager('scenes')
    light_controller = LightController(audio_listener, 'testing', scene_manager)
    audio_listener.start()
    light_controller.start()

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Current scene: {scene_manager.current_scene['name']}")
        stdscr.addstr(1, 0, "Available scenes:")
        for i, scene in enumerate(scene_manager.scenes):
            stdscr.addstr(i+2, 0, f"{scene}")
        
        stdscr.refresh()

        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == ord('s'):
            scene_manager.set_scene('static')
        elif key == ord('d'):
            scene_manager.set_scene('testing')

    audio_listener.stop()
    light_controller.stop()
    curses.endwin()

if __name__ == '__main__':
    main()



    