"""
This script contains the functions for converting input signals into DMX values based on the input parameters. Also stores colors and functions for converting colors to RGB values.

Author: Landry Bulls
Date: 8/24/24
"""

import numpy as np
import json
from config import audio_parameters

SAMPLERATE = audio_parameters['SAMPLERATE']
BLOCKSIZE = audio_parameters['BLOCKSIZE']

# these are DMX colors
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

def random_color():
    """
    Returns a random color from the color wheel
    """
    return np.random.choice(list(colors.keys()))

def generate_RGB_signal(brightness=255, color='pink', strobe=False, strobe_speed=255):
    """
    Returns the list of 7 DMX values for the RGB light
    """
    if strobe:
        strobe_val = 255
    else:
        strobe_val = 0
    if color == 'random':
        color = random_color()
    else:
        color = colors[color]
    return [brightness, colors[0], colors[1], colors[2], strobe_val, 0, 0]

def freq_to_index(freq):
    return int(round(freq * BLOCKSIZE / SAMPLERATE)) # This converts a frequency to an index in the FFT vector

def power_to_brightness(power, lower_threshold, upper_threshold, min_brightness=0, max_brightness=255):
    """
    Converts a power value to a brightness value based on the input thresholds.

    Parameters:
    power (float): The power value to convert to a brightness value.
    lower_threshold (float): The lower threshold for the power value under which the minimum brightness is used.
    upper_threshold (float): The upper threshold for the power value over which the maximum brightness is used.
    min_brightness (int): The minimum brightness value to use.
    max_brightness (int): The maximum brightness value to use.

    Returns:
    int: The brightness value to use. 
    """
    if power < lower_threshold:
        return min_brightness
    elif power > upper_threshold:
        return max_brightness
    else:
        return int((power - lower_threshold) / (upper_threshold - lower_threshold) * (max_brightness - min_brightness) + min_brightness)

def fft_to_rgb(fft_vec, frange=[0,2000], prange=[1.0, 15.0], brange=[0,255], color='random', strobe=False):
    """
    Converts an FFT vector to a set of DMX values to activate an RGB fixture. 

    Parameters:
    fft_vec (np.array): The FFT vector to convert to a DMX value.
    range (int): The range of the FFT vector to consider.
    lower_threshold (int): The lower threshold for the FFT sum under which the minimum brightness is used.
    upper_threshold (int): The upper threshold for the FFT sum over which the maximum brightness is used.
    min_brightness (int): The minimum brightness value to use.
    max_brightness (int): The maximum brightness value to use.
    strobe (bool): Whether to use strobe mode.

    Returns:
    int: The DMX value(s) to be sent to a given fixture. 
    """

    freq_low, freq_high = freq_to_index(frange[0]), freq_to_index(frange[1])
    fft_sum = np.sum(fft_vec[freq_low:freq_high])
    brightness = power_to_brightness(fft_sum, prange[0], prange[1], brange[0], brange[1])

    if color == 'random':
        color = random_color()
    else:
        color = colors[color]

    return generate_RGB_signal(brightness=brightness, color=color, strobe=strobe)

def fft_to_dimmer(fft_vec, frange, prange=[0.5,1.0], brange=[0,255]):
    """
    Converts an FFT vector to a dimmer value based on the sum of the FFT vector in a given range.

    Parameters:
    fft_vec (np.array): The FFT vector to convert to a DMX value.
    range (int): The range of the FFT vector to consider.
    lower_threshold (int): The lower threshold for the FFT sum under which the minimum brightness is used.
    upper_threshold (int): The upper threshold for the FFT sum over which the maximum brightness is used.
    min_brightness (int): The minimum brightness value to use.
    max_brightness (int): The maximum brightness value to use.

    Returns:
    int: The DMX value to be sent to a given dimmer. 
    """

    freq_low, freq_high = freq_to_index(frange[0]), freq_to_index(frange[1])
    fft_sum = np.sum(fft_vec[freq_low:freq_high])
    brightness = power_to_brightness(fft_sum, prange[0], prange[1], brange[0], brange[1])

    return brightness   

def fft_to_strobe(fft_vec, frange, lower_threshold=0.5):
    """
    Converts an FFT vector to a strobe value based on the sum of the FFT vector in a given range.
    For now, just returns the brightness value and whether to turn it on or off (255 or 0)

    Parameters:
    fft_vec (np.array): The FFT vector to convert to a DMX value.
    range (int): The range of the FFT vector to consider.
    lower_threshold (int): The lower threshold for the FFT sum under which the minimum brightness is used.
    upper_threshold (int): The upper threshold for the FFT sum over which the maximum brightness is used.
    min_brightness (int): The minimum brightness value to use.
    max_brightness (int): The maximum brightness value to use.

    Returns:
    int: The DMX value to be sent to a given dimmer. 
    """

    freq_low, freq_high = freq_to_index(frange[0]), freq_to_index(frange[1])
    fft_sum = np.sum(fft_vec[freq_low:freq_high])
    if fft_sum >= lower_threshold:
        return (255, 255)
    else:
        return (0, 0)
    

