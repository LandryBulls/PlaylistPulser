"""
Provides the AudioListener class, which listens to audio input and provides audio and FFT data using threading and queues.

Author: Landry Bulls
Date: 8/23/24
"""

import threading
import queue
import sounddevice as sd
import numpy as np
from scipy.fftpack import rfft
import time

class AudioListener(threading.Thread):
    def __init__(self, sample_rate=44100, block_size=2048, channels=1):
        threading.Thread.__init__(self)
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.fft_queue = queue.Queue()
        self.running = threading.Event()
        self.error_queue = queue.Queue()

    def run(self):
        def audio_callback(indata, frames, time, status):
            if status:
                self.error_queue.put(f"Audio callback error: {status}")
            try:
                audio_data = np.copy(indata[:, 0])
                fft_data = np.abs(rfft(audio_data))[:len(audio_data)//2]
                self.audio_queue.put(audio_data)
                self.fft_queue.put(fft_data)
            except Exception as e:
                self.error_queue.put(f"Error processing audio data: {str(e)}")

        self.running.set()
        try:
            with sd.InputStream(callback=audio_callback, channels=self.channels, 
                                samplerate=self.sample_rate, blocksize=self.block_size):
                while self.running.is_set():
                    sd.sleep(100)
        except Exception as e:
            self.error_queue.put(f"Error in audio stream: {str(e)}")

    def stop(self):
        self.running.clear()

    def get_audio_data(self):
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None

    def get_fft_data(self, timeout=0.08):
        try:
            return self.fft_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_errors(self):
        errors = []
        while not self.error_queue.empty():
            errors.append(self.error_queue.get_nowait())
        return errors

def main():
    audio_listener = AudioListener()
    audio_listener.start()
    print('Listening to audio...')

    try:
        while True:
            audio_data = audio_listener.get_audio_data()
            fft_data = audio_listener.get_fft_data()
            errors = audio_listener.get_errors()

            if errors:
                print("Errors occurred:", errors)

            if audio_data is not None and fft_data is not None:
                # Process data here
                pass

            sd.sleep(10)  # Small delay to prevent busy-waiting
    except KeyboardInterrupt:
        print("Stopping audio listener...")
    finally:
        audio_listener.stop()
        audio_listener.join()

if __name__ == "__main__":
    main()