# Playlist Pulser

The primary goal of this project at this point is to perform audio analysis in real time to map sounds to control DMX lights. 

There are four major layers. The minimal UI ran in the terminal, the logic to map audio features to lights, and the real-time reading of an audio stream and audio feature extract. 

As it stands, a while loop that runs in a jupyter notebook reads the data from what's playing over the background music, performs an FFT every 400ms chunk, and converts powers in different frequency bands to light properties like light identity, color, 
brightness, and the state of the DMX fixture. 

There are a few different mappings called "scenes" that are stored as dictionaries with parameters with keys (i.e., `bass_range`, `min_bass_brightness`, `strobe=True/False`). These dictonaries are then fed to functions that generate functions that are applied to each FFT vector and output a set of DMX commands based on the vector. 

I'm going to attempt to restructure it into different python scripts to make it more organized and actually work like a packge. 
