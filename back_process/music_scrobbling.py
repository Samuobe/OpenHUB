import subprocess
import time
import requests
import json
import configparser
import os


def get_current_metadata():
    try:
        status = subprocess.check_output(['playerctl', 'status'], stderr=subprocess.DEVNULL, text=True).strip().lower()
        if status != "playing":
            return None

        title = subprocess.check_output(['playerctl', 'metadata', 'title'], stderr=subprocess.DEVNULL, text=True).strip()
        artist = subprocess.check_output(['playerctl', 'metadata', 'artist'], stderr=subprocess.DEVNULL, text=True).strip()
        
        if not title:
            return None
            
        return {"artist": artist, "title": title}
    except subprocess.CalledProcessError:
        return None

def submit_listenbrainz(artist, title, listen_type="single"):
    if not LISTENBRAINZ_TOKEN or LISTENBRAINZ_TOKEN == "-":
        return

    url = "https://api.listenbrainz.org/1/submit-listens"
    headers = {
        "Authorization": f"Token {LISTENBRAINZ_TOKEN}",
        "Content-Type": "application/json"
    }

    artist_name = artist if artist else "Unknown Artist"

    # Creiamo prima l'oggetto payload base senza listened_at
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
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            print(f"🎵 Scrobble ListenBrainz ({listen_type}): {artist_name} - {title}")
        else:
            print(f"⚠️ Error ListenBrainz: {response.text}")
    except Exception as e:
        print(f"⚠️ Exception ListenBrainz: {e}")


def scrobbler_loop():
    last_played_song = None
    old_artist = None
    old_title = None
    start_time = 0
 
    config_main = configparser.ConfigParser()
    config_main.optionxform = str
    config_main.read("credential.env")
    LISTENBRAINZ_TOKEN = config_main.get("Subsonic", "ListenBrainz_key")
    if LISTENBRAINZ_TOKEN == "-":
        exit()
    
    print("🎧 ListenBrainz Scrobbler started...")
    while True:
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
                    
        time.sleep(10)

if __name__ == "__main__":
    scrobbler_loop()