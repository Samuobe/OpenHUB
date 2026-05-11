import os
import subprocess
import time
import discid
import musicbrainzngs
from pydub import AudioSegment
from mutagen.id3 import ID3, TIT2, TPE1, TALB, ID3NoHeaderError
from python_mpv_jsonipc import MPV

DEVICE = "/dev/sr0"
OUTPUT = "/tmp/fake_track.mp3"
USER_AGENT = "OpenHUB-CD-Module"
VERSION = "1.1"

musicbrainzngs.set_useragent(USER_AGENT, VERSION)

def init_mpv():
    try:
        # print("Initializing MPV...")
        return MPV()
    except Exception:
        # print(f"MPV start failed: {e}")
        return None


mpv_player = init_mpv()

def is_cd_inserted():
    try:
        discid.read(DEVICE)
        return True
    except Exception:
        return False

def get_cd_id():
    try:
        return discid.read(DEVICE).id
    except Exception:
        return None

def get_vlc_track_number():
    try:
        full_meta = subprocess.check_output(
            ["playerctl", "-p", "vlc", "metadata"], 
            stderr=subprocess.DEVNULL, text=True
        )

        for line in full_meta.splitlines():
            if "xesam:tracknumber" in line:
                parts = line.split()
                if parts:
                    return int(parts[-1])

        for line in full_meta.splitlines():
            if "mpris:trackid" in line:
                return int(line.split('/')[-1].replace("'", "")) + 1

    except Exception:
        pass
    
    return 1

def get_track_metadata(disc_id, track_number):
    # print(f"Querying MusicBrainz for track {track_number}...")
    try:
        result = musicbrainzngs.get_releases_by_discid(disc_id, includes=["artists", "recordings"])
        if 'disc' in result and result['disc']['release-list']:
            release = result['disc']['release-list'][0]
            album = release.get('title', "Audio CD")
            artist = release.get('artist-credit-phrase', "Unknown Artist")
            
            idx = track_number - 1
            try:
                tracks = release['medium-list'][0]['track-list']
                if 0 <= idx < len(tracks):
                    title = tracks[idx]['recording']['title']
                else:
                    title = f"Track {track_number}"
            except Exception:
                title = f"Track {track_number}"
            
            return title, artist, album
    except Exception:
        pass
    
    return f"Track {track_number}", "Unknown Artist", "Audio CD"

def write_and_load(title, artist, album):
    global mpv_player
    
    AudioSegment.silent(duration=180000).export(OUTPUT, format="mp3")
    

    try:
        tags = ID3(OUTPUT)
    except ID3NoHeaderError:
        tags = ID3()
        
    tags["TIT2"] = TIT2(encoding=3, text=title)
    tags["TPE1"] = TPE1(encoding=3, text=artist)
    tags["TALB"] = TALB(encoding=3, text=album)
    tags.save(OUTPUT)
    
    try:
        if not mpv_player:
            mpv_player = init_mpv()
        
        mpv_player.loadfile(OUTPUT, "replace")
        time.sleep(0.5)
        mpv_player.command("seek", 0, "absolute")
    except Exception:
        # print("Socket error, re-initializing MPV...")
        mpv_player = init_mpv()
        if mpv_player:
            mpv_player.loadfile(OUTPUT, "replace")

last_track = -1
last_disc = ""
is_active = False

# print("CD Metadata Daemon Started")

while True:
    if is_cd_inserted():
        is_active = True
        current_disc_id = get_cd_id()
        current_track_num = get_vlc_track_number()

        if current_disc_id != last_disc or current_track_num != last_track:
            # print(f"Change detected: Disc {current_disc_id} | Track {current_track_num}")
            
            metadata = get_track_metadata(current_disc_id, current_track_num)
            if metadata:
                write_and_load(metadata[0], metadata[1], metadata[2])
                last_disc = current_disc_id
                last_track = current_track_num
    else:
        if is_active:
            # print("CD removed. Stopping player.")
            try:
                if mpv_player:
                    mpv_player.command("stop")
            except Exception:
                pass
            last_disc = ""
            last_track = -1
            is_active = False
            
    time.sleep(1)