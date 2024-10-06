import requests
import time
import json
from bs4 import BeautifulSoup

class SpotifyAPIAuthless:
    """Access the Spotify API without Authentication using the temporary session IDs provided by the search API."""

    def getAccessToken(self):
        req = requests.get('https://open.spotify.com/search').text
        soup = BeautifulSoup(req, 'html.parser')
        script_tag = soup.find('script', {'id': 'session', 'data-testid': 'session', 'type': 'application/json'})
        if script_tag:
            self.script_tag = json.loads(script_tag.string)
        else:
            self.script_tag = None
            print("Script tag not found")

    def search(self, query, stype):
        if self.script_tag:
            access_token = self.script_tag.get('accessToken')
            if access_token:
                tries = 10
                while tries <= 10:
                    try:
                        req = requests.get(f'https://api.spotify.com/v1/search?query={query}&type={stype}', headers={'Authorization': f'Bearer {access_token}'})
                        if req.status_code == 401:
                            self.getAccessToken()
                            self.search(query, stype)
                            break
                        elif req.ok:
                            return req.json()['tracks']['items']
                    except:
                        time.sleep(1)
                        tries += 1
                if tries > 10:
                    raise Exception("Spotify's API failed to respond!")
    def getAlbumInfo(self, album):
        """Returns Spotify album info from album id."""
        if self.script_tag:
            access_token = self.script_tag.get('accessToken')
            if access_token:
                tries = 0
                while tries <= 10:
                    try:
                        req = requests.get(f'https://api.spotify.com/v1/albums/{album}', headers={'Authorization': f'Bearer {access_token}'})
                        if req.status_code == 401:
                            self.getAccessToken()
                            self.getAlbumInfo(album)
                            break
                        elif req.ok:
                            return req.json()
                    except:
                        time.sleep(1)
                        tries += 1
                if tries > 10:
                    raise Exception("Spotify's API failed to respond!")
    def getAlbumTracks(self, album, offset=0, limit=50):
        """Returns Spotify album tracks from album id."""
        if self.script_tag:
            access_token = self.script_tag.get('accessToken')
            if access_token:
                tries = 0
                while tries <= 10:
                    try:
                        req = requests.get(f'https://api.spotify.com/v1/albums/{album}/tracks?offset={offset}&limit={limit}', headers={'Authorization': f'Bearer {access_token}'})
                        if req.status_code == 401:
                            self.getAccessToken()
                            self.getAlbumInfo(album)
                            break
                        elif req.ok:
                            return req.json()
                    except:
                        time.sleep(1)
                        tries += 1
                if tries > 10:
                    raise Exception("Spotify's API failed to respond!")
    def getTrack(self, track):
        """Returns Spotify track info from track id."""
        if self.script_tag:
            access_token = self.script_tag.get('accessToken')
            if access_token:
                tries = 0
                while tries <= 10:
                    try:
                        req = requests.get(f'https://api.spotify.com/v1/tracks/{track}', headers={'Authorization': f'Bearer {access_token}'})
                        if req.status_code == 401:
                            self.getAccessToken()
                            self.getAlbumInfo(track)
                            break
                        elif req.ok:
                            return req.json()
                    except:
                        time.sleep(1)
                        tries += 1
                if tries > 10:
                    raise Exception("Spotify's API failed to respond!")
    def __init__(self):
        self.getAccessToken()