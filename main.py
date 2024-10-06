"""
Known bugs:
Features are tagged multiple times
Watch The Throne quality issues (should add a dictionary to query)
"""

"""
TODO:
Add composer data and much more data from Deezer when link is passed
Add feature info from Soundcloud (does NOT appear in ydl metadata)
Soundcloud tag with playlist image (currently only tags with individual song images, does NOT appear in ydl metadata)
Add tagging options for M4A and OPUS for the rest of the code
Enum the available formats to download to/warn that other formats won't be tagged
Do a general cleanup, this is very messy and has redundant code
Don't use YT-DLP for Soundcloud API
"""

import yt_dlp
import requests
import os
import time
import re
import base64
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
from colorama import Fore, Style
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TRCK, TYER, TPE2, TPOS
from ytmusicapi import YTMusic
from pytube import Playlist
from urllib.parse import urlparse
from musicdl.SpotifyAPI import SpotifyAPIAuthless
from musicdl.DeezerAPI import DeezerAPIAuthless


def querySearch(query, artistname='', albumname='', songname='', lengthseconds='', albumSyntax=False, explicit=True):
    ytmusic = YTMusic()
    search_results = ytmusic.search(query, filter='songs')
    song = ''
    if artistname and albumname and songname:
        if lengthseconds != 0:
            found = False
            for i in search_results:
                for x in i['artists']:
                    if x['name'].lower() == artistname.lower():
                        if (i['duration_seconds'] == lengthseconds+1 or i['duration_seconds'] == lengthseconds) and artistname == i['artists'][0]['name'] and explicit == i['isExplicit']:
                            found = True
                            song = i
                            break
                if found:
                    break
            if not found:
                print(Fore.YELLOW + f'[WARN]: Track {songname} could not be traditionally downloaded due to not being available on YouTube Music. Checking secondary uploads...' + Style.RESET_ALL)
                search_results = ytmusic.search(query, filter='videos')
                found = False
                for i in search_results:
                    if 'duration_seconds' in i:
                        if 'clean' not in songname.lower() and 'clean' not in i['title'].lower():
                            if i['duration_seconds'] == lengthseconds+1 or i['duration_seconds'] == lengthseconds or i['duration_seconds'] == lengthseconds-1:
                                song = i
                                found = True
                                return song
                if not found and not albumSyntax:
                    raise Exception(f'Could not download track {songname} because no primary or secondary downloads were found.')
                elif not found and albumSyntax:
                    print(Fore.RED + f'[ERROR]: Could not fetch track {songname} because no primary or secondary downloads were found.' + Style.RESET_ALL)
                    return False
        else:
            song = next(
                (i for i in search_results if any(x['name'].lower() == artistname.lower() and songname.lower().split('(feat.', 1)[0] == i['title'].lower().split('(feat.', 1)[0] for x in i['artists'])), 
                search_results[0]
            )
    else:
        song = search_results[0]
    return song

def downloadFromQuery(query, location='', bitrate=320, codec='mp3'):
    if re.match(r'https:\/\/soundcloud\.com\/[^\/]+\/[^\/]+', query):
        tries = dlerrortries = 0
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            sinfo = ytdl.extract_info(query, download=False)
        songtitle = sinfo['title']
        winSongTitle = songtitle.translate(str.maketrans('/\\<>:"|?*', '_________'))
        artist = sinfo['uploader']
        winArtistTitle = artist.translate(str.maketrans('/\\<>:"|?*', '_________'))
        ydl_opts = {
            'format': 'bestaudio[ext=opus]/bestaudio[acodec=opus]', # force OPUS intially, if it doesn't work after 5 attempts switch to M4A
            'outtmpl': f'{location}{winSongTitle} - {winArtistTitle}',
            'overwrites': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': bitrate,
            }]
        }
        while tries <= 10 and dlerrortries <= 5:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([query])
                    break
            except yt_dlp.utils.DownloadError:
                dlerrortries += 1
            except Exception:
                time.sleep(1)
                tries += 1
        if dlerrortries > 5:
            dlerrortries = tries = 0
            ydl_opts['format'] = 'bestaudio/best'
            while tries <= 10 and dlerrortries <= 5:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([query])
                        break
                except yt_dlp.utils.DownloadError:
                    dlerrortries += 1
                except Exception:
                    time.sleep(1)
                    tries += 1
        if tries >= 10:
            raise Exception(f"Couldn't download track {title}. YT-DLP error.")
        rdate = sinfo[rdate]
        rdate = f"{rdate[:4]}-{rdate[4:6]}-{rdate[6:]}"
        img = b''
        tries = 0
        while tries < 6:
            img = requests.get(sinfo['thumbnail'])
            if img.ok:
                img = img.content
                break
            else:
                tries += 1
                time.sleep(1)
        if tries > 5:
            print(Fore.RED + f'[ERROR]: Could not fetch cover art for {songtitle}. Is Soundcloud working as intended?' + Style.RESET_ALL)
        if codec.lower() == 'opus':
            audio = OggOpus(f"{location}{winSongTitle} - {artist}.{codec}") 
            pic = Picture()
            pic.data = img
            pic.type = 3
            pic.mime = "image/jpeg"
            audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode('ascii')]
            audio.update({"title": songtitle, "artist": artist, "comment": query, 'year': rdate, 'genre': sinfo.get('genre', 'Unknown')})
            audio.save()
        elif codec.lower() == 'm4a':
            audio = MP4(f"{location}{winSongTitle} - {artist}.{codec}")
            tags = {'covr': [MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)],
                '\xa9nam': songtitle,
                '\xa9ART': artist,
                '\xa9day': rdate,
                '\xa9gen': sinfo.get('genre', 'Unknown')
            }
            audio.update(tags)
            audio.save()
        return True
    elif re.match(r"https?://open\.spotify\.com/track/[a-zA-Z0-9]{22}", query):
        spotify = SpotifyAPIAuthless()
        trackid = urlparse(query).path.split('/')[2]
        sinfo = spotify.getTrack(trackid)
        title = sinfo['name']
        album = sinfo['album']['name']
        artist = ', '.join([artist['name'] for artist in sinfo['artists']])
        coverurl = sinfo['album']['images'][0]['url']
        winSongTitle = title.translate(str.maketrans('/\\<>:"|?*', '_________'))
        song = querySearch(title + ' ' + artist, explicit=sinfo['explicit'])
        if song['videoId'] == None:
            print(Fore.RED + f'[ERROR]: Could not fetch track from query {query} because no primary or secondary downloads were found.' + Style.RESET_ALL)
            return False
    else:
        song = querySearch(query)
        if song['videoId'] == None:
            print(Fore.RED + f'[ERROR]: Could not fetch track from query {query} because no primary or secondary downloads were found.' + Style.RESET_ALL)
            return False
        title = song['title']
        artist = ', '.join([artist['name'] for artist in song['artists']])
        album = song['album']['name']
        coverurl = song['thumbnails'][0]['url'].replace('w60-h60-l90-rj', 'w2000-h2000-l99-rj') # w2000-h2000 forces the max quality (usually 1400x1400 or 1425x1425), l99 forces a compression with 99% quality, rj returns as JPEG
        winSongTitle = title.translate(str.maketrans('/\\<>:"|?*', '_________')) # Windows doesn't support these characters in file names, so we replace them with an underscore

    img = b''
    tries = 0
    while tries < 6:
        img = requests.get(coverurl)
        if img.ok:
            img = img.content
            break
        else:
            tries += 1
            time.sleep(1)
    if tries > 5:
        print(Fore.RED + f'[ERROR]: Could not fetch cover art for {song["title"]}. Is YouTube Music working as intended?' + Style.RESET_ALL)

    outtmpl = f'{location}{winSongTitle} - {artist}.%(ext)s'

    ydl_opts = {
        'format': 'bestaudio[ext=opus]/bestaudio[acodec=opus]', # force OPUS intially, if it doesn't work after 5 attempts switch to M4A
        'outtmpl': outtmpl,
        'overwrites': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': codec,
            'preferredquality': bitrate,
        }]
    }

    tries = dlerrortries = 0

    while tries < 11 and dlerrortries < 6:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([song['videoId']])
                break
        except yt_dlp.utils.DownloadError as e:
            dlerrortries += 1
        except Exception:
            time.sleep(1)
            tries += 1
    if dlerrortries > 5:
        dlerrortries = 0
        tries = 0
        ydl_opts['format'] = 'bestaudio/best'
        while tries < 11 and dlerrortries < 6:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([song['videoId']])
                    break
            except yt_dlp.utils.DownloadError as e:
                dlerrortries += 1
            except Exception:
                time.sleep(1)
                tries += 1
    if tries >= 10:
        raise Exception(f"Couldn't download track {title}. YT-DLP error.")
    
    if codec.lower() == 'mp3':
        audio = MP3(f"{winSongTitle} - {artist}.{codec}", ID3=ID3)
        audio.tags.add(APIC(encoding=0,mime='image/jpeg',type=3,desc=u'Cover',data=img))
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TALB(encoding=3, text=album))
        audio.save()
    elif codec.lower() == 'm4a':
        audio = MP4(f"{winSongTitle} - {artist}.{codec}")
        audio.tags['covr'] = [MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)]
        audio.tags['\xa9nam'] = title
        audio.tags['\xa9ART'] = artist            
        audio.tags['\xa9alb'] = album
        audio.save()
    elif codec.lower() == 'opus':
        audio = OggOpus(f"{winSongTitle} - {artist}.{codec}") 
        pic = Picture()
        pic.data = img
        pic.type = 3
        pic.mime = "image/jpeg"
        audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode('ascii')]
        audio.update({"title": title, "artist": artist.replace("'", ""), "album": album})
        audio.save()


def downloadAlbum(query, bitrate=320, codec='mp3', forceytcoverart=False):
    """Downloads an album based off of a search query (only for YT Music), YouTube Music link, Spotify link, Deezer link, or Soundcloud link (only do this if it's a Soundcloud exclusive, the quality sucks)"""
    isThirdParty = False
    isSpotify = False
    isDeezer = False
    deezerfoundcopy = False
    spotfoundcopy = False
    realtracknum = 1
    def sanitize(name, isFolder=False):
        name = name.translate(str.maketrans('/\\<>:"|?*', '_________'))
        return name[:-1] if name[-1] == '.' and isFolder else name
    ytmusic = YTMusic()
    if re.match(r'https:\/\/soundcloud\.com\/[^\/]+\/[^\/]+', query):
        """
        Soundcloud auth implementing soon. For now this only downloads 96KBPS OPUS.
        """
        tries = dlerrortries = 0
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            sinfo = ytdl.extract_info(query, download=False)
        artist = sinfo['entries'][0]['uploader']
        albumtitle = sinfo['title']
        winAlbumTitle = albumtitle.translate(str.maketrans('/\\<>:"|?*', '_________'))
        winArtistName = artist.translate(str.maketrans('/\\<>:"|?*', '_________'))
        os.makedirs(f'./{winArtistName}/{winAlbumTitle}', exist_ok=True)
        realtracknum = 1
        for i in sinfo['entries']:
            if i['duration_string'] == '30': # previews for soundcloud go+
                realtracknum += 1
                print(Fore.YELLOW + f"[WARN]: Could not download track {i['title']} because it is only available for Soundcloud GO+ members." + Style.RESET_ALL)
                continue
            link = i['webpage_url']
            winSongTitle = i['title'].translate(str.maketrans('/\\<>:"|?*', '_________'))
            outtmpl = f'./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.%(ext)s'
            ydl_opts = {
            'format': 'bestaudio[ext=opus]/bestaudio[acodec=opus]', # force OPUS intially, if it doesn't work after 5 attempts switch to M4A
            'outtmpl': outtmpl,
            'overwrites': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': bitrate,
            }]
            }
            while tries < 11 and dlerrortries < 6:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([link])
                        rdate = i['upload_date']
                        rdate = f"{rdate[:4]}-{rdate[4:6]}-{rdate[6:]}"
                        for x in i['thumbnails']:
                            if x['id'] == 'original':
                                thumb = x['url']
                        img = b''
                        tries = 0
                        while tries < 6:
                            img = requests.get(thumb)
                            if img.ok:
                                img = img.content
                                break
                            else:
                                tries += 1
                                time.sleep(1)
                        if tries > 5:
                            print(Fore.RED + f'[ERROR]: Could not fetch cover art for {i["title"]}. Is Soundcloud working as intended?' + Style.RESET_ALL)
                    if codec.lower() == 'opus':
                        audio = OggOpus(f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}") 
                        pic = Picture()
                        pic.data = img
                        pic.type = 3
                        pic.mime = "image/jpeg"
                        audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode('ascii')]
                        audio.update({"title": i['title'], "artist": i['uploader'], "comment": link, 'year': rdate, 'genre': i['genre'], 'album': albumtitle, 'tracknumber': str(realtracknum)})
                        audio.save()
                    elif codec.lower() == 'm4a':
                        audio = MP4(f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}")
                        tags = {'covr': [MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)], '\xa9nam': i['title'], '\xa9ART': i['uploader'], '\xa9day': rdate, 'trkn': [(realtracknum, 0)], '\xa9alb': albumtitle, 'aART': artist, '\xa9gen': i['genre']}
                        audio.update(tags)
                        audio.save()
                    break
                except yt_dlp.utils.DownloadError as e:
                    dlerrortries += 1
                except Exception as e:
                    print(e)
                    time.sleep(1)
                    tries += 1
            if dlerrortries > 5:
                dlerrortries = 0
                tries = 0
                ydl_opts['format'] = 'bestaudio/best'
                while tries < 11 and dlerrortries < 6:
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([query])
                            break
                    except yt_dlp.utils.DownloadError as e:
                        dlerrortries += 1
                    except Exception:
                        time.sleep(1)
                        tries += 1
            realtracknum += 1
        if tries >= 10:
            raise Exception(f"Couldn't download track {i['title']}. YT-DLP error.")
        return
    elif re.match(r'https?://(?:www\.)?(?:music\.youtube\.com|youtube\.com)/playlist\?list=', query):
        if forceytcoverart:
            print(Fore.YELLOW + '[WARN]: forceytcoverart was passed but no Spotify link was added. This will do absolutely nothing.' + Style.RESET_ALL)
        playlist = Playlist(query)
        playlist_id = playlist.playlist_id
        vids = playlist.video_urls
        browse_id = ytmusic.get_album_browse_id(playlist_id)
        albuminfo = ytmusic.get_album(browse_id)
        ytmusictlist = []
        for i in albuminfo['tracks']:
            if i['isExplicit'] == True:
                ytmusictlist.append(i['title'])
            else:
                ytmusictlist.append(i['title'] + ' (clean)') # prevent overlap in certain releases
        albumtitle = albuminfo['title']
        folderartistname = ', '.join([artist['name'] for artist in albuminfo['artists']])
        fileartistname = '; '.join([artist['name'] for artist in albuminfo['artists']])
    elif re.match(r"https?://open\.spotify\.com/album/[a-zA-Z0-9]{22}", query):
        isThirdParty = True
        isSpotify = True
        spotify = SpotifyAPIAuthless()
        albumid = urlparse(query).path.split('/')[2]
        spalbuminfo = spotify.getAlbumInfo(albumid)
        albumtitle = spalbuminfo['name']
        explicit = False
        tlist = []
        if spalbuminfo['tracks']['total'] < spalbuminfo['tracks']['limit']:
            offset = 0
            totaltracks = 0
            while totaltracks <= spalbuminfo['tracks']['total']:
                data = spotify.getAlbumTracks(albumid, offset=offset, limit=spalbuminfo['tracks']['limit'])
                for i in data['items']:
                    totaltracks += 1
                    tlist.append(i['name'])
                    if i['explicit'] == True:
                        totaltracks = spalbuminfo['tracks']['total']+1
                        explicit = True
                offset += 1
        else:
            for i in spalbuminfo['tracks']['items']:
                tlist.append(i['name'])
                if i['explicit'] == True:
                    totaltracks = spalbuminfo['tracks']['total']+1
                    explicit = True
                    break
        albumreleasedate = spalbuminfo['release_date']
        if not forceytcoverart:
            coverurl = spalbuminfo['images'][0]['url']
        folderartistname = ', '.join([artist['name'] for artist in spalbuminfo['artists']])
        artistzero = spalbuminfo['artists'][0]['name']
        fileartistname = '; '.join([artist['name'] for artist in spalbuminfo['artists']])
        search_results = ytmusic.search(artistzero + ' ' + albumtitle.split('(feat.')[0].rstrip(' '), filter='albums')
        for i in search_results:
            if artistzero.lower().rstrip() == i['artists'][0]['name'].lower().rstrip() and (albumtitle.split('(feat.')[0].lower().rstrip(' ') in i['title'].split('(feat.')[0].lower().rstrip(' ')):
                album = i
                break
        albuminfo = ytmusic.get_album(album['browseId'])
        ytmusictlist = []
        for i in albuminfo['tracks']:
            if i['isExplicit'] == True:
                ytmusictlist.append(i['title'])
            else:
                ytmusictlist.append(i['title'] + ' (clean)')
        spotfoundcopy = False
        if album['title'].lower().rstrip() != albumtitle.lower().rstrip() and albuminfo.get('other_versions'):
            found = False
            for i in albuminfo['other_versions']:
                if i['title'].lower().rstrip() == albumtitle.lower().rstrip() and explicit == i['isExplicit']:
                    albuminfo = ytmusic.get_album(i['browseId'])
                    ytmusictlist = []
                    for i in albuminfo['tracks']:
                        if i['isExplicit'] == True:
                            ytmusictlist.append(i['title'])
                    else:
                        ytmusictlist.append(i['title'] + ' (clean)')
                    playlist = Playlist('https://www.youtube.com/playlist?list='+i['audioPlaylistId'])
                    vids = playlist.video_urls
                    found = True
                    spotfoundcopy = True
                    break
            if not found:
                print(Fore.YELLOW + '[WARN]: The specific edition of the album requested is not available in YouTube Music.' + Style.RESET_ALL)
                playlist = Playlist('https://www.youtube.com/playlist?list='+album['playlistId'])
                vids = playlist.video_urls
        else:
            playlist = Playlist('https://www.youtube.com/playlist?list='+album['playlistId'])
            vids = playlist.video_urls
    elif re.match(r"https:\/\/www\.deezer\.com\/(?:[^\/]+\/)?album\/(\d+)", query):
        isDeezer = True
        isThirdParty = True
        deezer = DeezerAPIAuthless()
        albumid = urlparse(query).path.split('/')[3]
        dalbuminfo = deezer.getAlbumInfo(albumid)
        albumtitle = dalbuminfo['results']['DATA']['ALB_TITLE']
        explicit = True if dalbuminfo['results']['DATA']['EXPLICIT_ALBUM_CONTENT']['EXPLICIT_LYRICS_STATUS'] == 1 else False
        tlist = []
        for i in dalbuminfo['results']['SONGS']['data']:
            tlist.append(i['SNG_TITLE'])
        albumreleasedate = dalbuminfo['results']['DATA']['ORIGINAL_RELEASE_DATE']
        if not forceytcoverart:
            coverurl = f"https://e-cdn-images.dzcdn.net/images/cover/{dalbuminfo['results']['DATA']['ALB_PICTURE']}/1500x1500-000000-90-0-0.jpg"
        folderartistname = ', '.join([artist['ART_NAME'] for artist in dalbuminfo['results']['DATA']['ARTISTS']])
        artistzero = dalbuminfo['results']['DATA']['ARTISTS'][0]['ART_NAME']
        fileartistname = '; '.join([artist['ART_NAME'] for artist in dalbuminfo['results']['DATA']['ARTISTS']])
        search_results = ytmusic.search(artistzero + ' ' + albumtitle.split('(feat.')[0].rstrip(' '), filter='albums')
        for i in search_results:
            if artistzero.lower().rstrip() == i['artists'][0]['name'].lower().rstrip() and (albumtitle.split('(feat.')[0].lower().rstrip(' ') in i['title'].split('(feat.')[0].lower().rstrip(' ')):
                album = i
                break
        albuminfo = ytmusic.get_album(album['browseId'])
        ytmusictlist = []
        for i in albuminfo['tracks']:
            if i['isExplicit'] == True:
                ytmusictlist.append(i['title'])
            else:
                ytmusictlist.append(i['title'] + ' (clean)')
        deezerfoundcopy = True
        for i in dalbuminfo['results']['SONGS']['data']:
            if i['EXPLICIT_TRACK_CONTENT']['EXPLICIT_LYRICS_STATUS'] == 1:
                explicit = True
                break
        if (albuminfo['title'].split('(feat.')[0].lower().rstrip(' ') != albumtitle.split('(feat.')[0].lower().rstrip(' ') or album['isExplicit'] != explicit) and albuminfo.get('other_versions'):
            deezerfoundcopy = False
            found = False
            for i in albuminfo['other_versions']:
                if i['title'].lower().rstrip() == albumtitle.lower().rstrip() and explicit == i['isExplicit']:
                    albuminfo = ytmusic.get_album(i['browseId'])
                    ytmusictlist = []
                    for i in albuminfo['tracks']:
                        if i['isExplicit'] == True:
                            ytmusictlist.append(i['title'])
                        else:
                            ytmusictlist.append(i['title'] + ' (clean)')
                    playlist = Playlist('https://www.youtube.com/playlist?list='+i['audioPlaylistId'])
                    vids = playlist.video_urls
                    found = True
                    deezerfoundcopy = True
                    break
            if not found:
                print(Fore.YELLOW + '[WARN]: The specific edition of the album requested is not available in YouTube Music.' + Style.RESET_ALL)
                playlist = Playlist('https://www.youtube.com/playlist?list='+album['playlistId'])
                vids = playlist.video_urls
        else:
            playlist = Playlist('https://www.youtube.com/playlist?list='+album['playlistId'])
            vids = playlist.video_urls
    else:
        if forceytcoverart:
            print(Fore.YELLOW + '[WARN]: forceytcoverart was passed but no Spotify link was added. This will do absolutely nothing.' + Style.RESET_ALL)
        search_results = ytmusic.search(query, filter='albums')
        album = search_results[0]
        playlist = Playlist('https://www.youtube.com/playlist?list='+album['playlistId'])
        vids = playlist.video_urls
        albumtitle = album['title']
        albuminfo = ytmusic.get_album(album['browseId'])
        ytmusictlist = []
        for i in albuminfo['tracks']:
            if i['isExplicit'] == True:
                ytmusictlist.append(i['title'])
            else:
                ytmusictlist.append(i['title'] + ' (clean)')
        folderartistname = ', '.join([artist['name'] for artist in albuminfo['artists']])
        fileartistname = '; '.join([artist['name'] for artist in albuminfo['artists']])
    vids = {k: v for k, v in zip(ytmusictlist, vids)}
    
    winArtistName = sanitize(albuminfo['artists'][0]['name'], isFolder=True)
    os.makedirs(f'./{winArtistName}', exist_ok=True)
    winAlbumTitle = sanitize(albumtitle, isFolder=True)
    if (forceytcoverart and isThirdParty) or not isThirdParty:
        coverurl = albuminfo['thumbnails'][0]['url'].replace('w60-h60-l90-rj', 'w2000-h2000-l90-rj') # change to w1000-h1000-rw for webp

    img = b''
    tries = 0
    while tries <= 5:
        img = requests.get(coverurl)
        if img.ok:
            img = img.content
            break
        else:
            tries += 1
            time.sleep(1)
    if tries > 5:
        print(Fore.RED + f'[ERROR]: Could not fetch cover art for {albumtitle}. Is YouTube Music working as intended?' + Style.RESET_ALL)
    if not spotfoundcopy and isSpotify:
        tracks = spalbuminfo['tracks']['items']
    elif not deezerfoundcopy and isDeezer:
        tracks = dalbuminfo['results']['SONGS']['data']
    else:
        tracks = albuminfo['tracks']
    for i in tracks:
        if not spotfoundcopy and isSpotify:
            stitle = i['name']
        elif not deezerfoundcopy and isDeezer:
            stitle = i['SNG_TITLE']
        else:
            stitle = i['title']

        artistsfile = [artist['name'] for artist in i['artists']]
        ogstitle = stitle

        if '(feat.' in stitle or 'FEAT.' in stitle: # FEAT. because of the issue with DAMN. and the collector's edition only being available on YT Music
            delimiter = '(feat.' if '(feat.' in stitle else 'FEAT.'
            features = stitle.split(delimiter)[1].rstrip(')').replace(' & ', ', ')
            artistsfile += features.split(', ')
            stitle = stitle.split(delimiter)[0].rstrip(' ')

        winSongTitle = sanitize(stitle)
        os.makedirs(f'./{winArtistName}/{winAlbumTitle}', exist_ok=True)

        videoid = ''
        if isSpotify:
            for z in vids:
                if z.lower().rstrip() in stitle.lower().rstrip():
                    videoid = vids[z]
                    break
        else:
            if i['isExplicit']:
                videoid = vids.get(ogstitle, '')
            else:
                videoid = vids.get(ogstitle+' (clean)', '')
        if videoid == '' and not spotfoundcopy and isSpotify:
            song = querySearch(i['name'] + ' ' + i['artists'][0]['name'], folderartistname, albumtitle, stitle, round(i['duration_ms']/1000))
            videoid = song['videoId']
        elif videoid == '':
            song = querySearch(i['title'] + ' ' + i['artists'][0]['name'], folderartistname, albumtitle, stitle, i['duration_seconds'])
            videoid = song['videoId']
        ydl_opts = {
                'format': 'bestaudio[ext=opus]/bestaudio[acodec=opus]', 
                'outtmpl': f'./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.%(ext)s',
                'overwrites': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec,
                    'preferredquality': bitrate,
                }]
            }
        tries = dlerrortries = 0

        while tries < 11 and dlerrortries < 6:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([videoid])
                    break
            except yt_dlp.utils.DownloadError:
                dlerrortries += 1
            except Exception:
                time.sleep(1)
                tries += 1

        if dlerrortries > 5:
            ydl_opts['format'] = 'bestaudio/best'
            tries = dlerrortries = 0

            while tries < 11 and dlerrortries < 6:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([videoid])
                    break
                except yt_dlp.utils.DownloadError:
                    dlerrortries += 1
                except Exception:
                    time.sleep(1)
                    tries += 1

        if tries >= 10:
            raise Exception(f"Couldn't download track {stitle}. YT-DLP error.")
        
        if codec.lower() == 'mp3':
            audio = MP3(f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}", ID3=ID3)
            audio.tags.add(APIC(encoding=0,mime='image/jpeg',type=3,desc=u'Cover',data=img))
            audio.tags.add(TIT2(encoding=3, text=stitle))
            audio.tags.add(TPE1(encoding=3, text=artistsfile))
            audio.tags.add(TRCK(encoding=3, text=str(realtracknum)))
            audio.tags.add(TALB(encoding=3, text=albumtitle))
            audio.tags.add(TYER(encoding=3, text=albumreleasedate if albumreleasedate is not None else albuminfo['year']))
            audio.tags.add(TPE2(encoding=3, text=fileartistname))
            if i.get('disc_number'):
                audio.tags.add(TPOS(encoding=3, text=str(i['disc_number'])))
            audio.save()
        if codec.lower() == 'm4a':
            audio = MP4(f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}")
            tags = {'covr': [MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)],
                '\xa9nam': stitle,
                '\xa9ART': artistsfile,
                '\xa9day': albumreleasedate if albumreleasedate is not None else albuminfo['year'],
                'trkn': [(realtracknum, 0)],
                '\xa9alb': albumtitle,
                'aART': fileartistname,
                'discnumber': [i['disc_number']]
            }
            audio.update(tags)
            audio.save()
        elif codec.lower() == 'opus':
            audio = OggOpus(f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}")
            audio.update({"date": albumreleasedate if albumreleasedate is not None else albuminfo['year'], "albumartist": fileartistname, "tracknumber": str(realtracknum)})
            pic = Picture()
            pic.data = img
            pic.type = 3
            pic.mime = "image/jpeg"
            audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode('ascii')]
            audio.update({"title": stitle, "artist": artistsfile, "album": albumtitle})
            if i.get('disc_number'):
                audio.update({'discnumber': str(i['disc_number'])})
            if isDeezer:
                audio.update({'discnumber': str(dalbuminfo['results']['SONGS']['data'][realtracknum-1]['DISK_NUMBER']), 'composer': ', '.join([artist for artist in dalbuminfo['results']['SONGS']['data'][realtracknum-1]['SNG_CONTRIBUTORS']['composer']]), 'comment': query})
            audio.save()
        realtracknum += 1
