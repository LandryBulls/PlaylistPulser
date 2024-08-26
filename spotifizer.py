import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import threading
import queue

# get the client id and client secret from the text file
with open('spotify_credentials.txt') as f:
    client_id = f.readline().strip().split(' ')[1]
    client_secret = f.readline().strip().split(' ')[1]
    uri = f.readline().split(' ')[1][:-1]
    username = f.readline().split(' ')[1]

uri = 'http://localhost:8000'

# set the environment variables
os.environ['SPOTIPY_CLIENT_ID'], os.environ['SPOTIFY_CLIENT_ID'] = client_id, client_id
os.environ['SPOTIPY_CLIENT_SECRET'], os.environ['SPOTIFY_CLIENT_SECRET'] = client_secret, client_secret
os.environ['SPOTIPY_REDIRECT_URI'], os.environ['SPOTIFY_REDIRECT_URI'] = uri, uri

auth_manager = SpotifyClientCredentials()
sp = spotipy.Spotify(auth_manager=auth_manager)

token = spotipy.util.prompt_for_user_token(username, scopes)

if token:
    sp = spotipy.Spotify(auth=token)
    saved_tracks_resp = sp.current_user_saved_tracks(limit=50)
else:
    print('Couldn\'t get token for that username')

user = sp.user(username)
sp.user = user

class Spotifizer(threading.Thread):
    def __init__(self):
        super().__init__()
        self.audio_queue = queue.Queue()
        self.running = threading.Event()
        self.error_queue = queue.Queue()

    def run(self):
        self.running.set()
        try:
            while self.running.is_set():
                # get the current track
                current_track = sp.current_playback()
                if current_track:
                    track_name = current_track['item']['name']
                    artist_name = current_track['item']['artists'][0]['name']
                    self.audio_queue.put(f"Currently playing: {track_name} by {artist_name}")
                    
                    # get the audio analysis of the current track
                    audio_analysis = sp.audio_analysis(track_id)

                    # get the audio features of the current track


                else:
                    self.audio_queue.put("No track currently playing")
        except Exception as e:
            self.error_queue.put(f"Error in audio stream: {str(e)}")

    def stop(self):
        self.running.clear()

    def get_audio_data(self):
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None

    def get_errors(self):
        errors = []
        while not self.error_queue.empty():
            errors.append(self.error_queue.get_nowait())
        return errors
