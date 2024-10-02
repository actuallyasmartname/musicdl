import yt_dlp
import requests
import base64
import os
import time
import re
from mutagen.mp3 import MP3
from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
from colorama import Fore, Style
from urllib.parse import urlparse, parse_qs
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TRCK, TYER
from ytmusicapi import YTMusic

def downloadFromQuery(query, location='', bitrate=320, albumSyntax=False, tracknum=0, codec='mp3', artistname='', albumname='', songname='', coverurl='', clean=False, year='0', plays='', lengthseconds=0):
    ytmusic = YTMusic()
    search_results = ytmusic.search(query, filter='songs')
    song = ''
    if artistname and albumname and songname:
        if lengthseconds != 0 and plays != '':
            found = False
            for i in search_results:
                for x in i['artists']:
                    if x['name'].lower() == artistname.lower() and songname.lower().split('(feat.', 1)[0] == i['title'].lower().split('(feat.', 1)[0]:
                        songinfo = ytmusic.get_album(i['album']['id'])
                        for z in songinfo['tracks']:
                            if i['title'] == z['title'] and plays == z['views']:
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
                                break
                if found == False and not albumSyntax:
                    raise Exception(f'Could not download track {songname} because no primary or secondary downloads were found.')
                elif found == False and albumSyntax:
                    print(Fore.RED + f'[ERROR]: Could not fetch track {songname} because no primary or secondary downloads were found.' + Style.RESET_ALL)
                    return False
        else:
            song = next(
                (i for i in search_results if any(
                    x['name'].lower() == artistname.lower() and 
                    songname.lower().split('(feat.', 1)[0] == i['title'].lower().split('(feat.', 1)[0]
                    for x in i['artists']
                )), 
                search_results[0]
            )
    else:
        song = search_results[0]
    if song['videoId'] == None:
        if not albumSyntax:
            raise Exception(f'Could not download track {songname} because there is no video ID tied to the top search result. This usually happens during downtime or, rarely, another SESAC like situation.')
        else:
            print(Fore.RED + f'[ERROR]: Could not fetch track {songname} because no primary or secondary downloads were found.' + Style.RESET_ALL)
            return False
    if artistname != '' and albumname != '' and songname != '':
        title = songname
        artist = artistname
        album = albumname
    else:
        title = song['title']
        artist = ', '.join([artist['name'] for artist in song['artists']])
        album = song['album']['name']
        coverurl = song['thumbnails'][0]['url'].replace('w60-h60-l90-rj', 'w1000-h1000')
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
        print(Fore.RED + f'[ERROR]: Could not fetch cover art for {songname}. Is YouTube Music working as intended?' + Style.RESET_ALL)

    outtmpl = f'{location}{tracknum}. {winSongTitle}.%(ext)s' if albumSyntax else f'{location}{winSongTitle} - {artist}.%(ext)s'

    ydl_opts = {
        'format': 'bestaudio[ext=opus]/bestaudio/best', # prefer opus due to its quality, else download m4a
        'outtmpl': outtmpl,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': codec,
            'preferredquality': bitrate
        }],
    }

    tries = 0
    while tries < 11:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([song['videoId']])
                break
        except Exception:
            time.sleep(1)
            tries += 1
    if tries >= 10:
        raise Exception(f"Couldn't download track {title}. YT-DLP error.")
    
    if codec.lower() == 'mp3':
        if albumSyntax == True:
            audio = MP3(f"{location}{tracknum}. {winSongTitle}.{codec}", ID3=ID3)
        else:
            audio = MP3(f"{winSongTitle} - {artist}.{codec}", ID3=ID3)
        audio.tags.add(APIC(encoding=0,mime='image/jpeg',type=3,desc=u'Cover',data=img))
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))
        if albumSyntax == True:
            audio.tags.add(TYER(encoding=3, text=year))
            audio.tags.add(TRCK(encoding=3, text=str(tracknum)))
        audio.tags.add(TALB(encoding=3, text=album))
        audio.save()

def downloadAlbum(query, bitrate=320):
    custracknum = 0
    def sanitize(name):
        name = name.translate(str.maketrans('/\\<>:"|?*', '_________'))
        return name[:-1] if name[-1] == '.' else name
    ytmusic = YTMusic()
    if re.match(r'https?://(?:www\.)?(?:music\.youtube\.com|youtube\.com)/playlist\?list=', query):
        query_params = parse_qs(urlparse(query).query)
        playlist_id = query_params.get('list', [None])[0]
        browse_id = ytmusic.get_album_browse_id(playlist_id)
        albuminfo = ytmusic.get_album(browse_id)
        albumtitle = albuminfo['title']
        artistname = ', '.join([artist['name'] for artist in albuminfo['artists']])
    else:
        search_results = ytmusic.search(query, filter='albums')
        album = search_results[0]
        artistname = ', '.join([artist['name'] for artist in album['artists']])
        albumtitle = album['title']
        albuminfo = ytmusic.get_album(album['browseId'])
    winArtistName = sanitize(artistname)
    if winArtistName.lower().rstrip() == 'jay z':
        winArtistName == 'JAY-Z'
    os.makedirs(f'./{winArtistName}', exist_ok=True)
    winAlbumTitle = sanitize(albumtitle)
    coverurl = albuminfo['thumbnails'][0]['url'].replace('w60-h60-l90-rj', 'w1000-h1000')

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
        print(Fore.RED + f'[ERROR]: Could not fetch cover art for {albumtitle}. Is YouTube Music working as intended?' + Style.RESET_ALL)

    for i in albuminfo['tracks']:
        custracknum += 1
        stitle = i['title']
        artists = ', '.join([artist['name'] for artist in i['artists']])
        winSongTitle = stitle.translate(str.maketrans('/\\<>:"|?*', '_________'))
        codec = 'mp3'
        os.makedirs(f'./{winArtistName}/{winAlbumTitle}', exist_ok=True)
        print(i)          
        if i['videoType'] == 'MUSIC_VIDEO_TYPE_OMV' and '(audio)' not in stitle.lower():
            downloadFromQuery(artistname + ' ' + stitle, f'./{winArtistName}/{winAlbumTitle}/', bitrate, True, i['trackNumber'], artistname=artists, albumname=albumtitle, songname=stitle,coverurl=coverurl, year=albuminfo['year'], lengthseconds=i['duration_seconds'], plays=i['views'])
        elif i['videoType'] == None:
            didireturn = downloadFromQuery(artistname + ' ' + stitle, f'./{winArtistName}/{winAlbumTitle}/', bitrate, True, custracknum, artistname=artists, albumname=albumtitle, songname=stitle,coverurl=coverurl, year=albuminfo['year'],lengthseconds=i['duration_seconds'], plays=i['views'])
            if didireturn == False:
                continue
        else:      
            ydl_opts = {
                'format': 'bestaudio[ext=opus]/bestaudio/best', 
                'outtmpl': f'./{winArtistName}/{winAlbumTitle}/{i["trackNumber"]}. {winSongTitle}.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec,
                    'preferredquality': bitrate
                }],
            }
            tries = 0
            while tries < 11:
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([i['videoId']])
                        break
                except Exception:
                    time.sleep(1)
                    tries += 1
            if tries >= 10:
                raise Exception(f"Couldn't download track {stitle}. YT-DLP error.")
            audio = MP3(f"./{winArtistName}/{winAlbumTitle}/{i['trackNumber']}. {winSongTitle}.{codec}", ID3=ID3)
            audio.tags.add(APIC(encoding=0,mime='image/jpeg',type=3,desc=u'Cover',data=img))
            audio.tags.add(TIT2(encoding=3, text=i['title']))
            audio.tags.add(TPE1(encoding=3, text=artists))
            audio.tags.add(TRCK(encoding=3, text=str(i['trackNumber'])))
            audio.tags.add(TALB(encoding=3, text=i['album']))
            audio.tags.add(TYER(encoding=3, text=albuminfo['year']))
            audio.save()
