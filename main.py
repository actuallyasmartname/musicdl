"""
Known bugs:
Features are tagged multiple times
Watch The Throne quality issues (should add a dictionary to query)
Some tracks download twice for some reason
"""

"""
TODO:
Add extra data from Deezer when link is passed
Let Spotify and Deezer be passed through downloadFromQuery
Add feature info from Soundcloud (does NOT appear in ydl metadata)
Soundcloud tag with playlist image (currently only tags with individual song images, does NOT appear in ydl metadata)
Enum the available formats to download to and warn that other formats won't be tagged
Do a general cleanup, this is very messy and has redundant code
Don't use YT-DLP for Soundcloud API
Soundcloud GO+ authentication options
Apple Music API support
Album downloads to specified location
"""

import yt_dlp
import requests
import os
import time
import re
import base64
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
from colorama import Fore, Style
from mutagen.id3 import ID3, APIC, TPE2, TPOS, COMM, TCOM
from ytmusicapi import YTMusic
from pytube import Playlist
from urllib.parse import urlparse
from SpotifyAPI import SpotifyAPIAuthless
from DeezerAPI import DeezerAPIAuthless

def tagAudio(**kwargs):
    if 'tags' and 'codec' and 'audio' not in kwargs:
        raise Exception('Passed incorrect argument to tagAudio. This shouldn\'t happen unless this function is being used outside of the main script.')
    try:
        codec = kwargs['codec']
        if codec == 'mp3':
            audio = MP3(kwargs['audio'], ID3=EasyID3)
            for i in kwargs['tags']:
                audio[i] = kwargs['tags'][i]
            if kwargs.get('picture'):
                audio.save()
                audio = MP3(kwargs['audio'], ID3=ID3)
                audio.tags.add(APIC(encoding=0,mime='image/jpeg',type=3,desc=u'Cover',data=kwargs['picture']))
            audio.save()
        elif codec == 'opus':
            audio : OggOpus = kwargs['audio']
            audio.update(kwargs['tags'])
            pic = Picture()
            pic.data = kwargs['picture']
            pic.mime = 'image/jpeg'
            pic.type = 3
            audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode('ascii')]
            audio.save()
        elif codec == 'm4a':
            audio : MP4 = kwargs['audio']
            audio.update(kwargs['tags'])
            audio.save()
    except Exception as e:
        raise Exception(f'Failed to tag audio because {e}')

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
        with yt_dlp.YoutubeDL({'quiet': True}) as ytdl:
            sinfo = ytdl.extract_info(query, download=False)
        try:
            songtitle = sinfo['title']
        except:
            raise Exception("Link passed was not a valid Soundcloud track! Make sure it's not a set/album and the track exists.")
        winSongTitle = songtitle.translate(str.maketrans('/\\<>:"|?*', '_________'))
        artist = sinfo['uploader']
        winArtistTitle = artist.translate(str.maketrans('/\\<>:"|?*', '_________'))
        ydl_opts = {
            'format': 'bestaudio[ext=opus]/bestaudio[acodec=opus]',
            'outtmpl': f'{location}{winSongTitle} - {winArtistTitle}',
            'overwrites': True,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec, 'preferredquality': bitrate,}]
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
            tagAudio(audio=audio, tags={"title": songtitle, "artist": artist, "comment": query, 'year': rdate, 'genre': sinfo.get('genre', 'Unknown')}, picture=img, codec='opus')
        elif codec.lower() == 'm4a':
            audio = MP4(f"{location}{winSongTitle} - {artist}.{codec}")
            tagAudio(audio=audio, tags={'covr': [MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)], '\xa9nam': songtitle, '\xa9ART': artist, '\xa9day': rdate, '\xa9gen': sinfo.get('genre', 'Unknown')}, codec='m4a')
        return True
    elif re.match(r"https?://open\.spotify\.com/track/[a-zA-Z0-9]{22}", query):
        raise Exception('spotify implementation in progress')
        """
        spotify = SpotifyAPIAuthless()
        trackid = urlparse(query).path.split('/')[2]
        sinfo = spotify.getTrack(trackid)
        title = sinfo['name']
        album = sinfo['album']['name']
        artist = ', '.join([artist['name'] for artist in sinfo['artists']])
        coverurl = sinfo['album']['images'][0]['url']
        winSongTitle = title.translate(str.maketrans('/\\<>:"|?*', '_________'))
        song = querySearch(title + ' ' + artist, explicit=sinfo['explicit'])
        if not song['videoId']:
            print(Fore.RED + f'[ERROR]: Could not fetch track from query {query} because no primary or secondary downloads were found.' + Style.RESET_ALL)
            return False
        """
    else:
        song = querySearch(query)
        if not song['videoId']:
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
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec, 'preferredquality': bitrate}]
    }

    tries = dlerrortries = 0
    while tries <= 10 and dlerrortries <= 5:
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
        tries = dlerrortries = 0
        ydl_opts['format'] = 'bestaudio/best'
        while tries <= 10 and dlerrortries <= 5:
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
        audio = f"{location}{winSongTitle} - {artist}.{codec}"
        tagAudio(audio=audio, tags={'title': title, 'artist': artist, 'album': album}, picture=img, codec='mp3')
    elif codec.lower() == 'm4a':
        audio = MP4(f"{location}{winSongTitle} - {artist}.{codec}")
        tagAudio(audio=audio, tags={'covr': [MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)], '\xa9nam': title, '\xa9ART': artist, '\xa9alb': album}, codec='m4a')
    elif codec.lower() == 'opus':
        audio = OggOpus(f"{location}{winSongTitle} - {artist}.{codec}") 
        tagAudio(audio=audio, tags={'title': title, 'artist': artist.replace("'", ""), 'album': album}, picture=img)

def downloadAlbum(query, bitrate=320, codec='mp3', forceytcoverart=False):
    """Downloads an album based off of a search query (only for YT Music), YouTube Music link, Spotify link, Deezer link, or Soundcloud link (only do this if it's a Soundcloud exclusive, the quality sucks)"""
    isThirdParty = False
    isSpotify = False
    albumreleasedate = ''
    isDeezer = False
    deezerfoundcopy = False
    spotfoundcopy = False
    realtracknum = 1
    def sanitize(name, isFolder=False):
        name = name.translate(str.maketrans('/\\<>:"|?*', '_________'))
        return name[:-1] if name[-1] == '.' and isFolder else name
    ytmusic = YTMusic()
    if re.match(r'https:\/\/soundcloud\.com\/[^\/]+\/[^\/]+', query) and not re.match(r'https:\/\/soundcloud\.com\/[^\/]+\/sets\/[^\/]+', query):
        raise Exception('This is a soundcloud track link, not a set link! Use downloadFromQuery to download tracks.')
    if re.match(r'https:\/\/soundcloud\.com\/[^\/]+\/sets\/[^\/]+', query):
        """
        Soundcloud auth implementing soon. For now this only downloads 96KBPS OPUS.
        """
        tries = dlerrortries = 0
        with yt_dlp.YoutubeDL({'quiet': True}) as ytdl:
            sinfo = ytdl.extract_info(query, download=False)
        try:
            artist = sinfo['entries'][0]['uploader']
        except:
            raise Exception("Link passed was not a valid Soundcloud set!")
        albumtitle = sinfo['title']
        winAlbumTitle = albumtitle.translate(str.maketrans('/\\<>:"|?*', '_________'))
        winArtistName = artist.translate(str.maketrans('/\\<>:"|?*', '_________'))
        os.makedirs(f'./{winArtistName}/{winAlbumTitle}', exist_ok=True)
        realtracknum = 1
        for i in sinfo['entries']:
            if i['duration_string'] == '30' and i['format'] == 'http_mp3_128_preview - audio only': # previews for soundcloud go+
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
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec, 'preferredquality': bitrate}]
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
                        tagAudio(audio=audio, tags={"title": i['title'], "artist": i['uploader'], "comment": link, 'year': rdate, 'genre': i['genre'], 'album': albumtitle, 'tracknumber': str(realtracknum)}, codec='opus', picture=img)
                    elif codec.lower() == 'm4a':
                        audio = MP4(f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}")
                        tagAudio(audio=audio, tags={'covr': [MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)], '\xa9nam': i['title'], '\xa9ART': i['uploader'], '\xa9day': rdate, 'trkn': [(realtracknum, 0)], '\xa9alb': albumtitle, 'aART': artist, '\xa9gen': i['genre']}, codec='m4a')
                    elif codec.lower() == 'mp3':
                        audio = f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}"
                        tagAudio(audio=audio, tags={'title': i['title'], 'artist': i['uploader'], 'album': albumtitle}, picture=img, codec='mp3')
                    break
                except yt_dlp.utils.DownloadError as e:
                    dlerrortries += 1
                except Exception as e:
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
        vids = playlist.video_urls
        albuminfo = ytmusic.get_album(ytmusic.get_album_browse_id(playlist.playlist_id))
        ytmusictlist = []
        for i in albuminfo['tracks']:
            if i['isExplicit']:
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
        othertlist = []
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
                    othertlist.append(i)
                    if i['explicit']:
                        totaltracks = spalbuminfo['tracks']['total']+1
                        explicit = True
                offset += 1
        else:
            for i in spalbuminfo['tracks']['items']:
                othertlist.append(i)
                tlist.append(i['name'])
                if i['explicit']:
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
        album = None
        for i in search_results:
            if albumtitle == 'good kid, m.A.A.d city':
                albumtitle = 'good kid, m.A.A.d. city' # yt music at it again
            if any(artistzero.lower().rstrip()  == artist['name'].lower().rstrip() for artist in i['artists']) and (i['title'].lower().rstrip() in albumtitle.lower().rstrip() or i['title'].lower().rstrip() == albumtitle.lower().rstrip()):
                album = i
                break
        vids = {}
        if not album:
            ytmusictlist = []
            for i in othertlist:
                song = querySearch(i['name'] + ' ' + artistzero, artistzero, albumtitle, i['name'], round(i['duration_ms']/1000))
            print(Fore.YELLOW + '[WARN]: The specific edition of the album requested is not available in YouTube Music.' + Style.RESET_ALL)
        else:
            albuminfo = ytmusic.get_album(album['browseId'])
            ytmusictlist = []
            for i in albuminfo['tracks']:
                if i['isExplicit']:
                    ytmusictlist.append(i['title'])
                else:
                    ytmusictlist.append(i['title'] + ' (clean)')
            spotfoundcopy = True
            if album['title'].lower().rstrip() != albumtitle.lower().rstrip() and albuminfo.get('other_versions'):
                found = False
                for i in albuminfo['other_versions']:
                    if i['title'].lower().rstrip() == albumtitle.lower().rstrip() and explicit == i['isExplicit']:
                        albuminfo = ytmusic.get_album(i['browseId'])
                        ytmusictlist = []
                        for i in albuminfo['tracks']:
                            if i['isExplicit']:
                                ytmusictlist.append(i['title'])
                        else:
                            ytmusictlist.append(i['title'] + ' (clean)')
                        playlist = Playlist('https://www.youtube.com/playlist?list='+albuminfo['audioPlaylistId'])
                        vids = playlist.video_urls
                        found = True
                        break
                if not found:
                    spotfoundcopy = False
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
            coverurl = f"https://cdn-images.dzcdn.net/images/cover/{dalbuminfo['results']['DATA']['ALB_PICTURE']}/1500x1500-000000-90-0-0.jpg"
        folderartistname = ', '.join([artist['ART_NAME'] for artist in dalbuminfo['results']['DATA']['ARTISTS']])
        artistzero = dalbuminfo['results']['DATA']['ARTISTS'][0]['ART_NAME']
        fileartistname = '; '.join([artist['ART_NAME'] for artist in dalbuminfo['results']['DATA']['ARTISTS']])
        search_results = ytmusic.search(artistzero + ' ' + albumtitle.split('(feat.')[0].rstrip(' '), filter='albums')
        for i in search_results:
            if artistzero.lower().rstrip() == i['artists'][0]['name'].lower().rstrip() and (albumtitle.split('(feat.')[0].lower().rstrip(' ') in i['title'].split('(feat.')[0].lower().rstrip(' ') or i['title'].split('(feat.')[0].lower().rstrip(' ') in albumtitle.split('(feat.')[0].lower().rstrip(' ')):
                album = i
                break
        albuminfo = ytmusic.get_album(album['browseId'])
        ytmusictlist = []
        for i in albuminfo['tracks']:
            if i['isExplicit']:
                ytmusictlist.append(i['title'])
            else:
                ytmusictlist.append(i['title'] + ' (clean)')
        deezerfoundcopy = True
        for i in dalbuminfo['results']['SONGS']['data']:
            if i['EXPLICIT_TRACK_CONTENT']['EXPLICIT_LYRICS_STATUS'] == 1:
                explicit = True
                break
        if (albuminfo['title'].split('(feat.')[0].lower().rstrip(' ') != albumtitle.split('(feat.')[0].lower().rstrip(' ') or album['isExplicit'] != explicit) and albuminfo.get('other_versions'):
            found = False
            for i in albuminfo['other_versions']:
                if i['title'].lower().rstrip() == albumtitle.lower().rstrip() and explicit == i['isExplicit']:
                    albuminfo = ytmusic.get_album(i['browseId'])
                    ytmusictlist = []
                    for i in albuminfo['tracks']:
                        if i['isExplicit']:
                            ytmusictlist.append(i['title'])
                        else:
                            ytmusictlist.append(i['title'] + ' (clean)')
                    playlist = Playlist('https://www.youtube.com/playlist?list='+albuminfo['audioPlaylistId'])
                    vids = playlist.video_urls
                    found = True
                    break
            if not found:
                deezerfoundcopy = False
                print(Fore.YELLOW + '[WARN]: The specific edition of the album requested is not available in YouTube Music.' + Style.RESET_ALL)
                playlist = Playlist('https://www.youtube.com/playlist?list='+album['playlistId'])
                vids = playlist.video_urls
        else:
            playlist = Playlist('https://www.youtube.com/playlist?list='+album['playlistId'])
            vids = playlist.video_urls
    else:
        if forceytcoverart:
            print(Fore.YELLOW + '[WARN]: forceytcoverart was passed but no third-party link was passed. This will do absolutely nothing.' + Style.RESET_ALL)
        search_results = ytmusic.search(query, filter='albums')
        album = search_results[0]
        playlist = Playlist('https://www.youtube.com/playlist?list='+album['playlistId'])
        vids = playlist.video_urls
        albumtitle = album['title']
        albuminfo = ytmusic.get_album(album['browseId'])
        ytmusictlist = []
        for i in albuminfo['tracks']:
            if i['isExplicit']:
                ytmusictlist.append(i['title'])
            else:
                ytmusictlist.append(i['title'] + ' (clean)')
        folderartistname = ', '.join([artist['name'] for artist in albuminfo['artists']])
        fileartistname = '; '.join([artist['name'] for artist in albuminfo['artists']])
    if spotfoundcopy or deezerfoundcopy:
        pass
    else:
        vids = {k: v for k, v in zip(ytmusictlist, vids)}
    if isSpotify:
        winArtistName = sanitize(artistzero, isFolder=True)
    else:
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
        if spotfoundcopy or deezerfoundcopy:
            videoid = vids[realtracknum-1]
        elif not deezerfoundcopy or not spotfoundcopy:
            for z in vids:
                if stitle.lower().rstrip().replace('(', '').replace(')', '') in z.lower().rstrip().replace('(', '').replace(')', ''):
                    videoid = vids[z]
                    break
        else:
            if i['isExplicit']:
                videoid = vids.get(ogstitle, '')
            else:
                videoid = vids.get(ogstitle+' (clean)', '')
        if videoid == '' and isSpotify:
            song = querySearch(i['name'] + ' ' + i['artists'][0]['name'], folderartistname, albumtitle, stitle, round(i['duration_ms']/1000))
            videoid = song['videoId']
        elif videoid == '':
            song = querySearch(i['title'] + ' ' + i['artists'][0]['name'], folderartistname, albumtitle, stitle, i['duration_seconds'])
            videoid = song['videoId']
        ydl_opts = {
                'format': 'bestaudio[ext=opus]/bestaudio[acodec=opus]', 
                'outtmpl': f'./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.%(ext)s',
                'overwrites': True,
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': codec, 'preferredquality': bitrate}]
            }
        tries = dlerrortries = 0

        while tries <= 10 and dlerrortries <= 5:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(videoid, download=True) # use later
                    break
            except yt_dlp.utils.DownloadError:
                dlerrortries += 1
            except Exception as e:
                time.sleep(1)
                tries += 1

        if dlerrortries > 5:
            ydl_opts['format'] = 'bestaudio/best'
            tries = dlerrortries = 0
            while tries <= 10 and dlerrortries <= 5:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(videoid, download=True) # use later
                    break
                except yt_dlp.utils.DownloadError:
                    dlerrortries += 1
                except Exception:
                    time.sleep(1)
                    tries += 1
        if tries >= 10:
            raise Exception(f"Couldn't download track {stitle}. YT-DLP error.")
        if codec.lower() == 'mp3':
            audio = f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}"
            mp3audiohere = MP3(audio, ID3=ID3)
            mp3audiohere.tags.add(APIC(encoding=0,mime='image/jpeg',type=3,desc=u'Cover',data=img))
            mp3audiohere.tags.add(TPE2(encoding=3, text=fileartistname))
            if i.get('disc_number'):
                mp3audiohere.tags.add(TPOS(encoding=3, text=str(i['disc_number'])))
            if isDeezer:
                mp3audiohere.tags.add(COMM(encoding=3, text=query))
                mp3audiohere.tags.add(TPOS(encoding=3, text=str(dalbuminfo['results']['SONGS']['data'][realtracknum-1]['DISK_NUMBER'])))
                mp3audiohere.tags.add(TCOM(encoding=3, text=', '.join([value for key, values in dalbuminfo['results']['SONGS']['data'][realtracknum-1]['SNG_CONTRIBUTORS'].items() if key != 'main_artist' for value in values])))
            mp3audiohere.save()
            tagAudio(audio=audio, tags={'title': stitle, 'artist': artistsfile, 'album': albumtitle, 'tracknumber': str(realtracknum), 'date': albumreleasedate if albumreleasedate is not None else albuminfo['year']}, codec='mp3')
        if codec.lower() == 'm4a':
            audio = MP4(f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}")
            tagAudio(audio=audio, tags={'covr': [MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)], '\xa9nam': stitle, '\xa9ART': artistsfile, '\xa9day': albumreleasedate if albumreleasedate is not None else albuminfo['year'], 'trkn': [(realtracknum, 0)], '\xa9alb': albumtitle, 'aART': fileartistname, 'discnumber': [i['disc_number']]}, codec='m4a')
        elif codec.lower() == 'opus':
            audio = OggOpus(f"./{winArtistName}/{winAlbumTitle}/{realtracknum}. {winSongTitle}.{codec}")
            tags = {"date": albumreleasedate if albumreleasedate is not None else albuminfo['year'], "albumartist": fileartistname, "tracknumber": str(realtracknum), "title": stitle, "artist": artistsfile, "album": albumtitle}
            if i.get('disc_number'):
                tags['discnumber'] = str(i['disc_number'])
            if isDeezer:
                tags['discnumber'] = str(dalbuminfo['results']['SONGS']['data'][realtracknum-1]['DISK_NUMBER'])
                tags['composer'] = ', '.join([value for key, values in dalbuminfo['results']['SONGS']['data'][realtracknum-1]['SNG_CONTRIBUTORS'].items() if key != 'main_artist' for value in values])
            tagAudio(audio=audio, tags=tags, picture=img, codec='opus')
        realtracknum += 1
