from pydub import AudioSegment
from mutagen.id3 import ID3, TIT2, TPE1, TALB, ID3NoHeaderError
from python_mpv_jsonipc import MPV
import time
import discid
import musicbrainzngs

def is_cd_inserted(device="/dev/sr0"):
    try:
        discid.read(device)
        return True
    except Exception:
        return False

def get_cd_id(device="/dev/sr0"):
    try:
        disco = discid.read(device)
        return disco.id
    except Exception as e:
        print(f"Error reding disk ID: {e}")
        return None

def get_vlc_track_number():
   # print("Cerco VLC")
    try:
        result = subprocess.check_output(
            ["playerctl", "-p", "vlc", "metadata", "mpris:trackid"], 
            stderr=subprocess.STDOUT, text=True
        ).strip()
        
        track_number = int(result.split('/')[-1]) + 1
        return track_number
    except Exception:
        try:
            res = subprocess.check_output(
                ["playerctl", "-p", "vlc", "metadata", "vlc:track_number"], 
                text=True
            ).strip()
            return int(res)
        except:
            return 1 

musicbrainzngs.set_useragent("OpenHUB-CD-Module", "1.0")

def get_track_metadata(disc_id, track_number):
    #print("Cerco copertina")
    #print(f"ID: {disc_id}   track_number: {track_number}")
    try:
        result = musicbrainzngs.get_releases_by_discid(disc_id, includes=["artists", "recordings"])
        #print("Trovata")
        if 'disc' in result and result['disc']['release-list']:
            release = result['disc']['release-list'][0]
            
            album = release.get('title', "Unknown Album")
            artist = release.get('artist-credit-phrase', "Unknown Artist")
            
            track_index = track_number - 1
            
            try:
                track_list = release['medium-list'][0]['track-list']
                if 0 <= track_index < len(track_list):
                    track_title = track_list[track_index]['recording']['title']
                else:
                    track_title = f"Track {track_number}"
            except (KeyError, IndexError):
                track_title = f"Track {track_number}"
                
            return track_title, artist, album
            
    except Exception as e:
        print(f"Error MusicBrainz: {e}")
    
    return None

def write_data(title, artist, album):
    OUTPUT = "/tmp/fake_track.mp3"
    try:
        os.remove(OUTPUT)
    except:
        pass
    

    TITLE = title
    ARTIST = artist
    ALBUM = album

    AudioSegment.silent(duration=180000).export(OUTPUT, format="mp3")

    try:
        tags = ID3(OUTPUT)
    except ID3NoHeaderError:
        tags = ID3()

    tags["TIT2"] = TIT2(encoding=3, text=TITLE)
    tags["TPE1"] = TPE1(encoding=3, text=ARTIST)
    tags["TALB"] = TALB(encoding=3, text=ALBUM)
    tags.save(OUTPUT)

    #print("Fake MP3 creato")

    try:
        mpv = MPV(
            ipc_timeout=10, 
            start_mpv=True, 
            vo="null", 
            ao="null", 
            no_config=True
        )
       
    except Exception as e:
        mpv = None
    mpv.loadfile(OUTPUT, "replace")

    time.sleep(1)

    mpv.command("seek", 0, "absolute")

    #print("Playing")

while True:
   # print("Avvio")
    if is_cd_inserted():
       # print("CD TROVATO")
        cd_id = get_cd_id()
        if cd_id != None:
           # print("ID TROVATO")
            metadata = get_track_metadata(cd_id, get_vlc_track_number())
            if metadata != None:
               # print("METADATA TROVATI: ", metadata)
                write_data(metadata[0], metadata[1], metadata[2])

    time.sleep(1)
