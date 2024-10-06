import requests
import time
import random
import math

class DeezerAPIAuthless:
    """Access the Deezer API without Authentication using the temporary session IDs provided by a specific API request."""
    def getAccessToken(self,):
        self.session = requests.sessions.Session()
        self.cid = math.floor(1e9 * random.random())
        req = self.session.post(f'https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token=&cid={self.cid}').json()
        self.accessToken = req['results']['checkForm']
    def getAlbumInfo(self, album):
        """Returns Spotify album info from album id."""
        tries = 0
        while tries <= 10:
            try:
                req = self.session.post(f'https://www.deezer.com/ajax/gw-light.php?method=deezer.pageAlbum&input=3&api_version=1.0&api_token={self.accessToken}&cid={self.cid}', json={"alb_id":str(album),"lang":"us","tab":0,"header":True})
                if req.status_code == 401:
                    self.getAccessToken()
                    self.getAlbumInfo(album)
                    break
                elif not req.ok:
                    tries += 1
                    continue
                elif req.ok:
                    return req.json()
            except:
                time.sleep(1)
                tries += 1
        if tries > 10:
            raise Exception("Spotify's API failed to respond!")
    def __init__(self):
        self.getAccessToken()