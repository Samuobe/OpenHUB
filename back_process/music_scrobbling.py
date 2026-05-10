import subprocess
import time
import requests
import json
import configparser
import os
import discid
import musicbrainzngs

LISTENBRAINZ_TOKEN = None

def is_placeholder(text):
    if not text or text.strip().lower() in ("unknown", "audio cd", "cd audio"):
        return True
    if text.strip().lower().startswith("track") or text.strip().lower().startswith("traccia"):
        return True
    return False

def get_musicbrainz_metadata(track_number=1, device="/dev/sr0"):
    try:
        musicbrainzngs.set_useragent("OpenHUB", "0.1", "https://github.com/Samuobe/OpenHUB")
        disc = discid.read(device)
        disc_id = disc.id
        res = musicbrainzngs.get_releases_by_discid(disc_id, includes=["recordings", "artists"])
        releases = res.get('disc', {}).get('release-list', [])
        if not releases:
            return None, None
        release = releases[0]
        artist = release['artist-credit'][0]['artist']['name'] if 'artist-credit' in release else "CD Audio"
        # Cerca tracce
        tracks = []
        for medium in release.get('medium-list', []):
            for track in medium.get('track-list', []):
                tracks.append(track['recording']['title'])
        title = tracks[track_number-1] if 0 < track_number <= len(tracks) else f"Traccia {track_number}"
        return artist, title
    except Exception as e:
        print(f"[MusicBrainz] Lookup failed: {e}")
        return None, None

def get_current_metadata():
    ALLOWED_PLAYERS = ["vlc", "mpv"]
    try:
        player_name = subprocess.check_output(
            ['playerctl', 'metadata', '--format', '{{playerName}}'],
            stderr=subprocess.DEVNULL, text=True).strip().lower()
        if not any(allowed in player_name for allowed in ALLOWED_PLAYERS):
            return None

        status = subprocess.check_output(
            ['playerctl', 'status'],
            stderr=subprocess.DEVNULL, text=True).strip().lower()
        if status != "playing":
            return None

        artist = subprocess.check_output(
            ['playerctl', 'metadata', 'artist'],
            stderr=subprocess.DEVNULL, text=True).strip()
        title = subprocess.check_output(
            ['playerctl', 'metadata', 'title'],
            stderr=subprocess.DEVNULL, text=True).strip()
        url = subprocess.check_output(
            ['playerctl', 'metadata', 'xesam:url'],
            stderr=subprocess.DEVNULL, text=True).strip()
        try:
            tracknumber = int(subprocess.check_output(
                ['playerctl', 'metadata', 'xesam:tracknumber'],
                stderr=subprocess.DEVNULL, text=True).strip())
        except Exception:
            tracknumber = 1

        if artist and title and not is_placeholder(title):
            return {"artist": artist, "title": title}

        if url.startswith("cdda://"):
            print("[Meta] MPRIS vuoto, provo lookup MusicBrainz...")
            mb_artist, mb_title = get_musicbrainz_metadata(tracknumber)
            if mb_artist and mb_title and not is_placeholder(mb_title):
                print(f"[Meta] MusicBrainz: {mb_artist} - {mb_title}")
                return {"artist": mb_artist, "title": mb_title}
            # Altrimenti, almeno titoli base
            return {"artist": "CD Audio", "title": f"Traccia {tracknumber}"}

        return None

    except subprocess.CalledProcessError as e:
        print(f"[Meta] playerctl error: {e}")
        return None
    except Exception as ex:
        print(f"[Meta] error: {ex}")
        return None

def submit_listenbrainz(artist, title, listen_type="single"):
    global LISTENBRAINZ_TOKEN
    if not LISTENBRAINZ_TOKEN or LISTENBRAINZ_TOKEN == "-":
        return

    url = "https://api.listenbrainz.org/1/submit-listens"
    headers = {
        "Authorization": f"Token {LISTENBRAINZ_TOKEN}",
        "Content-Type": "application/json"
    }

    artist_name = artist if artist else "Unknown Artist"

    payload_item = {
        "track_metadata": {
            "artist_name": artist_name,
            "track_name": title
        }
    }
    if listen_type == "single":
        payload_item["listened_at"] = int(time.time())

    data = {
        "listen_type": listen_type,
        "payload": [payload_item]
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"🎵 Scrobble ListenBrainz ({listen_type}): {artist_name} - {title}")
        else:
            print(f"⚠️ Error ListenBrainz: {response.text}")
    except Exception as e:
        print(f"⚠️ Exception ListenBrainz: {e}")

def scrobbler_loop():
    global LISTENBRAINZ_TOKEN
    last_played_song = None
    old_artist = None
    old_title = None
    start_time = 0
 
    config_main = configparser.ConfigParser()
    config_main.optionxform = str
    config_main.read("credential.env")
    LISTENBRAINZ_TOKEN = config_main.get("Subsonic", "ListenBrainz_key")
    if LISTENBRAINZ_TOKEN == "-":
        print("ListenBrainz token not set. Exiting.")
        exit()
    
    print("🎧 ListenBrainz Scrobbler started...")
    while True:
        try:
            if not os.path.isfile("operations_data/music_scrobbling_lock.status"):
                current_song = get_current_metadata()

                current_id = f"{current_song['artist']}-{current_song['title']}" if current_song else None

                if current_id != last_played_song:
                    if last_played_song is not None and start_time > 0:
                        play_duration = time.time() - start_time
                        if play_duration >= 30:
                            submit_listenbrainz(old_artist, old_title, listen_type="single")

                    last_played_song = current_id

                    if current_song:
                        old_artist = current_song['artist']
                        old_title = current_song['title']
                        start_time = time.time()
                        submit_listenbrainz(current_song['artist'], current_song['title'], listen_type="playing_now")
                    else:
                        start_time = 0
                        old_artist = None
                        old_title = None

        except Exception as e:
            print(f"[Scrobbler loop error] {e}")
        time.sleep(10)

if __name__ == "__main__":
    scrobbler_loop()