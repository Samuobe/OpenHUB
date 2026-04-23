import configparser
from caldav import DAVClient
import requests
import datetime
import subprocess
from dateutil import rrule
import vlc
import hashlib
import random
import string
import difflib
import os
import signal
import time
import urllib.parse
from functions.mpv_status import is_mpv_running
import alsaaudio
from other_windows.settings import open_settings_page
from other_windows.bluetooth_manager import open_bluetooth_window
from PyQt6.QtCore import QTimer

mixer = alsaaudio.Mixer()
    
#SET ENV
config = configparser.ConfigParser()
config.optionxform = str 
config.read("credential.env")

device_name = config.get("Device info", "device_name")

caldav_url = config.get("CALDAV", "caldav_url")
caldav_username = config.get("CALDAV", "caldav_username")
caldav_password = config.get("CALDAV", "caldav_password")

home_assistant_url = config.get("Home Assistant", "home_assistant_url")
home_assistant_token = config.get("Home Assistant", "home_assistant_token")

subsonic_url = config.get("Subsonic", "subsonic_url")
subsonic_username = config.get("Subsonic", "subsonic_username")
subsonic_password = config.get("Subsonic", "subsonic_password")


#SET CALDAV
try:
    client = DAVClient(caldav_url, username=caldav_username, password=caldav_password)
    principal = client.principal()
    calendars = principal.calendars()
    caldav_on = True
except:
    print("ERROR CONNECTING TO RADICALE")
    caldav_on= False

#SET HOME ASSISTANT
HOME_ASSISTANT_HEADERS = {
    "Authorization": f"Bearer {home_assistant_token}",
    "Content-Type": "application/json",
}

##support funciotn:
def get_states():
    url = f"{home_assistant_url}/api/states"
    response = requests.get(url, headers=HOME_ASSISTANT_HEADERS)
    try:
        return response.json()
    except Exception:
        print("❌ JSON parsing error")
        print("Status:", response.status_code)
        print("Response:", response.text)
        return None

# ==========================================
# REAL FUNCTION
# ==========================================


def stop():
    return "STOP SIGNAL"

def manage_music(action: str = None, song_name: str = None):
    global player
    
    if action:
        action = action.lower().strip()
        if "next" in action: action = "next"
        if "prev" in action: action = "previous"
        if "pause" in action: action = "pause"
        if "play" in action: action = "play"

    if action in ["pause", "play", "previous", "next"]:
        print("RICHIESTA MUSIC=", action)
        if is_mpv_running():
            os.system(f'playerctl -p "mpv" {action}')
        else:
            os.system(f"playerctl {action}")
        return f"Music {action} executed"
        
    elif action == "stop":
        os.system("killall mpv")
        os.system("playerctl pause")
    elif action == "music":
        if subsonic_url == "-" or subsonic_username == "-" or subsonic_password == "-":
            return "Attenction, subsonic is not configurated, configure it in setting"

        player = None
        def create_token(password):
            salt = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            token = hashlib.md5((password + salt).encode()).hexdigest()
            return token, salt

        def get_auth():
            token, salt = create_token(subsonic_password)
            return {
                "u": subsonic_username,
                "t": token,
                "s": salt,
                "v": "1.16.1",
                "c": f"{device_name.replace(' ', '-')}_via-OpenHomeHUB",
                "f": "json"
            }

        def play_urls(urls, title=""):
            pid_file = "operations_data/music_pid.txt"
            playlist_file = "operations_data/playlist.m3u"
            
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, "r") as f:
                        old_pid = int(f.read().strip())
                    os.kill(old_pid, signal.SIGTERM)
                except Exception:
                    pass 
            
            os.makedirs("operations_data", exist_ok=True)
            with open(playlist_file, "w") as f:
                for u in urls:
                    f.write(u + "\n")
            
            p = subprocess.Popen(
                ["mpv", "--no-video", f"--playlist={playlist_file}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            with open(pid_file, "w") as f:
                f.write(str(p.pid))

            print(f"\n▶️ In riproduzione (Coda di {len(urls)} brani): {title}")
            print("🔗 ELENCO URL IN CODA:")
            for url in urls:
                print(f" - {url}")

        def stream_url(song_id):
            params = get_auth()
            params["id"] = song_id
            query = urllib.parse.urlencode(params)
            return f"{subsonic_url}/rest/stream.view?{query}"

        def random_song():
            params = get_auth()
            params["size"] = 20 #SIZE OF MUSIC LIST
            r = requests.get(f"{subsonic_url}/rest/getRandomSongs.view", params=params).json()
            songs = r["subsonic-response"]["randomSongs"].get("song", [])
            
            if songs:
                urls = [stream_url(s["id"]) for s in songs]
                play_urls(urls, "Mix Casuale continuo")

        def search_and_play(query):
            if query.lower().strip() == "random":
                random_song()
                return "I put a random music mix"

            params = get_auth()
            params["query"] = query

            r = requests.get(f"{subsonic_url}/rest/search3.view", params=params).json()
            result = r["subsonic-response"].get("searchResult3", {})

            songs = result.get("song", [])
            albums = result.get("album", [])    
            artists = result.get("artist", [])
            playlists = result.get("playlist", [])

            query_lower = query.lower().strip()

            for album in albums:
                album_name = album.get("title", album.get("name", ""))
                if album_name.lower() == query_lower or query_lower in album_name.lower():
                    params_alb = get_auth()
                    params_alb["id"] = album["id"]
                    r_alb = requests.get(f"{subsonic_url}/rest/getAlbum.view", params=params_alb).json()
                    album_songs = r_alb["subsonic-response"]["album"].get("song", [])
                    
                    urls = [stream_url(s["id"]) for s in album_songs]
                    if urls:
                        play_urls(urls, f"Album: {album_name}")
                        return f"I'm playing the entire album {album_name}"

            for playlist in playlists:
                playlist_name = playlist.get("name", playlist.get("title", ""))
                if playlist_name.lower() == query_lower or query_lower in playlist_name.lower():
                    params_play = get_auth()
                    params_play["id"] = playlist["id"]
                    r_play = requests.get(f"{subsonic_url}/rest/getPlaylist.view", params=params_play).json()
                    playlist_songs = r_play["subsonic-response"]["playlist"].get("entry", [])
                    
                    urls = [stream_url(s["id"]) for s in playlist_songs]
                    if urls:
                        play_urls(urls, f"Playlist: {playlist_name}")
                        return f"I'm playing the playlist {playlist_name}"

            for song in songs:
                if song["title"].lower() == query_lower or query_lower in song["title"].lower():
                    urls = [stream_url(song["id"])]
                    
                    params_rnd = get_auth()
                    params_rnd["size"] = 20
                    r_rand = requests.get(f"{subsonic_url}/rest/getRandomSongs.view", params=params_rnd).json()
                    for rand_s in r_rand["subsonic-response"]["randomSongs"].get("song", []):
                        if rand_s["id"] != song["id"]:
                            urls.append(stream_url(rand_s["id"]))
                            
                    play_urls(urls, song["title"])
                    return f"I'm playing the song {song['title']} followed by a random mix"

            for artist in artists:
                artist_name = artist.get("name", "")
                if artist_name.lower() == query_lower or query_lower in artist_name.lower():
                    params_art = get_auth()
                    params_art["id"] = artist["id"]
                    r_art = requests.get(f"{subsonic_url}/rest/getArtist.view", params=params_art).json()
                    artist_albums = r_art["subsonic-response"]["artist"].get("album", [])
                    
                    urls = []
                    for alb in artist_albums:
                        params_alb = get_auth()
                        params_alb["id"] = alb["id"]
                        r_alb = requests.get(f"{subsonic_url}/rest/getAlbum.view", params=params_alb).json()
                        for s in r_alb["subsonic-response"]["album"].get("song", []):
                            urls.append(stream_url(s["id"]))
                        if len(urls) > 50: #Music list
                            break
                    if urls:
                        play_urls(urls, f"Artista: {artist_name}")
                        return f"I'm playing songs by {artist_name}"

            available_albums = [a.get("title", a.get("name", "")) for a in albums][:5]
            available_songs = [s["title"] for s in songs][:10]
            available_artists = [a["name"] for a in artists][:5]
            available_playlists = [p.get("name", p.get("title", "")) for p in playlists][:5]

            if not available_songs and not available_artists and not available_playlists and not available_albums:
                params = get_auth()
                params["size"] = 15
                r_rand = requests.get(f"{subsonic_url}/rest/getRandomSongs.view", params=params).json()
                rand_songs = [s["title"] for s in r_rand["subsonic-response"]["randomSongs"].get("song", [])]
                return f"No matches found for '{query}'. Available random songs: {rand_songs}. Evaluate them and call manage_music again with the exact name, or use 'random'."

            response_text = f"No EXACT match found for '{query}'. However, I found these related items. "
            if available_albums: response_text += f"Albums: {available_albums}. "
            if available_songs: response_text += f"Songs: {available_songs}. "
            if available_artists: response_text += f"Artists: {available_artists}. "
            if available_playlists: response_text += f"Playlists: {available_playlists}. "
            
            response_text += "Please analyze this list considering possible speech-to-text spelling errors. Pick the most likely match and call this tool AGAIN using that EXACT name. If they are completely different, pass 'random' as song_name."
            
            return response_text

        print("SONG NAME=", song_name)
        if song_name == None:
            random_song()
            response = "I put a random music mix"
        else:
            response = search_and_play(song_name)
        return response

    else:
        return "Segnalate this error: CODE ERROR; NO VALID ACTION FOR MANAGE MUSIC"
 
def manage_events(date: str, time: str, description: str, action: int):
    print(f"\n📅 EVENTO: {description} IL {date} ALLE {time} AZIONE: {action}\n")
    return "Evento salvato localmente."

def get_events(limit: int = 15):
    if caldav_url == "-" or caldav_username == "-" or caldav_username == "-":
        return "Error, caldav is not configurated, configure it in settings"
    if not caldav_on:
        return "Error, caldav not available"
    
    all_parsed_events = []
    now = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    one_year_later = now + datetime.timedelta(days=365)

    for cal in calendars:
        try:
            events = cal.search(start=now, end=one_year_later, event=True, expand=False)

            for event in events:
                ical = event.icalendar_instance
                for component in ical.walk():
                    if component.name == "VEVENT":
                        summary = str(component.get('summary', 'Senza titolo'))
                        dtstart_prop = component.get('dtstart')
                        if not dtstart_prop: continue
                        
                        dtstart = dtstart_prop.dt

                        if not isinstance(dtstart, datetime.datetime):
                            dtstart = datetime.datetime.combine(dtstart, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
                        elif dtstart.tzinfo is None:
                            dtstart = dtstart.replace(tzinfo=datetime.timezone.utc)

                        if component.get('rrule'):
                            rrule_obj = component.get('rrule')
                            rrule_str = rrule_obj.to_ical().decode()

                            if "FREQ=YEARLY" in rrule_str and "BYMONTH=" not in rrule_str:
                                rrule_str += f";BYMONTH={dtstart.month}"
                            try:
                                rule = rrule.rrulestr(rrule_str, dtstart=dtstart)
                                occurences = rule.between(now, one_year_later, inc=True)                                
                                for occ in occurences:
                                    if occ.tzinfo is None:
                                        occ = occ.replace(tzinfo=datetime.timezone.utc)
                                    
                                    all_parsed_events.append({
                                        "summary": summary,
                                        "start_dt": occ,
                                        "display": occ.strftime("%d/%m/%Y")
                                    })
                            except Exception as e:
                                print(f"Errore rrule su {summary}: {e}")
                        else:
                            if now <= dtstart <= one_year_later:
                                all_parsed_events.append({
                                    "summary": summary,
                                    "start_dt": dtstart,
                                    "display": dtstart.strftime("%d/%m/%Y")
                                })
        except Exception as e:
            print(f"Errore calendario: {e}")

    all_parsed_events.sort(key=lambda x: x["start_dt"])
    formatted = []
    seen = set()
    for e in all_parsed_events:
        line = f"{e['summary']} | {e['display']}"
        if line not in seen:
            seen.add(line)
            formatted.append(line)

    return formatted[:limit] if formatted else "Nessun evento."

def home_assistant(action: int, device_input: str):
    if home_assistant_url == "-" or home_assistant_token == "-":
        return "Error, home assistant is not configurated, configure it in settings"  
    states = get_states()
    if not states:
        print("❌ No states received")
        return None

    requested_device = None
    for entity in states:
        eid = entity.get("entity_id")
        state = entity.get("state")
        if state in [None, "unknown", "unavailable"]:
            continue
        if device_input.lower() in eid.lower():
            requested_device = {"entity_id": eid, "state": state}

    if action == 0: 
        return {"requested_device": requested_device}

    if action in [1, 2]:  
        if not requested_device:
            print(f"❌ Device non trovato: {device_input}")
            return None

        entity_id = requested_device["entity_id"]
        domain = entity_id.split(".")[0]
        service = "turn_on" if action == 1 else "turn_off"
        url = f"{home_assistant_url}/api/services/{domain}/{service}"
        data = {"entity_id": entity_id}

        response = requests.post(url, headers=HOME_ASSISTANT_HEADERS, json=data)
        if response.status_code in [200, 201]:
            print(f"✅ {entity_id} {service} executed")
            return {"entity_id": entity_id, "new_state": service}
        else:
            print(f"❌ Failed to execute {service} on {entity_id}")
            return None

def weather():
    return "Say to the user: whatch out of your window"

def timer(name: str = None, time: str=None, tipe: str=0):
    os.makedirs("operations_data", exist_ok=True)
    if name == None:
        if tipe == 0: #timer
            name="Timer"
        else:
            name = "Alarm"
    try:
        with open("operations_data/clock.txt", "r") as f:
            file_data = f.read()
        with open("operations_data/clock.txt", "w") as f:
            f.write(file_data)
            f.write(f"\n{name}|{time}|{tipe}")
    except:
        with open("operations_data/clock.txt", "w") as f:
            f.write(f"\n{name}|{time}|{tipe}")
    
    if tipe == 0:
        return "timer set"
    else:
        return "allarm set"
        
def manage_volume(action: str = None, volume: int = None):
    action = action.lower()
    if action == "set":
        if volume == None:
            return "I can't set a volume if you don't say to me the value"
        mixer.setvolume(volume)
        return f"Volume set at {volume}"
    elif action == "increases":
        original_volume = mixer.getvolume()[0]
        if volume == None:
            modify = 5
        else:
            modify = volume
        mixer.setvolume(original_volume+ modify)
        return f"Volume increased at {volume+modify}"
    elif action == "reduce":
        original_volume = mixer.getvolume()[0]
        if volume == None:
            modify = 5
        else:
            modify = volume
        mixer.setvolume(original_volume- modify)
        return f"Volume decreased at {volume-modify}"
    elif action =="error":
        return f"Volume value out of range"
    else:
        return f"Segnalate this error: Invalid volume_mange action: {action}"
    
def get_backend_paired_devices():
    devices = []
    result = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Device"):
            parts = line.split(" ", 2)
            if len(parts) >= 2:
                mac = parts[1].strip().upper()
                name = parts[2].strip() if len(parts) > 2 else "Sconosciuto"
                info_text = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
                if "Paired: yes" in info_text:
                    is_connected = "Connected: yes" in info_text
                    devices.append({"name": name, "mac": mac, "connected": is_connected})
    return devices

def bluetooth_actions(action: str = None, device_name: str = None):
    action = action.lower().strip() if action else ""
    
    if action not in ["connect", "disconnect"]:
        return "Error, no valid action specified. Use 'connect' or 'disconnect'."
    if not device_name:
        return "Error, no device specified."
        
    devices = get_backend_paired_devices()

    if not devices:
        return "No paired Bluetooth devices found on this system. Pair a device from settings first."

    device_names = [d['name'] for d in devices]
    device_name_lower = device_name.lower().strip()

    target_device = None
    for d in devices:
        if d['name'].lower().strip() == device_name_lower:
            target_device = d
            break
            
    if not target_device:
        for d in devices:
            if device_name_lower in d['name'].lower():
                target_device = d
                break

    if not target_device:
        response_text = (
            f"No EXACT match found for '{device_name}'. Available paired devices are: {device_names}. "
            "Please analyze this list considering possible speech-to-text spelling errors. "
            "Pick the most likely match and call this tool AGAIN using that EXACT name."
        )
        return response_text

    mac = target_device['mac']
    actual_name = target_device['name']

    if action == "connect":
        subprocess.run(["bluetoothctl", "connect", mac], capture_output=True)
        time.sleep(1.5)
        info_text = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
        if "Connected: yes" in info_text:
            return f"Successfully connected to Bluetooth device {actual_name}."
        else:
            return f"Failed to connect to {actual_name}. Tell the user to make sure the device is turned on and nearby."
            
    elif action == "disconnect":
        subprocess.run(["bluetoothctl", "disconnect", mac], capture_output=True)
        time.sleep(1.5)
        info_text = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True).stdout
        if "Connected: yes" not in info_text:
            return f"Successfully disconnected from Bluetooth device {actual_name}."
        else:
            return f"Failed to disconnect from {actual_name}."

# Aggiungi questa variabile fuori dalle funzioni
window_to_open = None

def open_window(window: str=None):
    global window_to_open
    
    if window == None:
        return "Error, i don't undestood what window i need to open"
        
    if window == "settings":
        window_to_open = "settings"
        return "Tells the user that the Settings page is opening."
        
    elif window == "bluetooth": 
        window_to_open = "bluetooth"
        return "Tells the user that the Bluetooth page is opening."
        
    else:
        return "Error, this window option doen not exist"



# ==========================================
# FUNCTION MAPPING 
# ==========================================

available_functions = {
    "manage_music": manage_music,
    "manage_events": manage_events,
    "get_events": get_events,
    "home_assistant": home_assistant,
    "stop": stop,
    "timer": timer,
    "manage_volume" : manage_volume,
    "bluetooth_actions": bluetooth_actions,
    "open_window": open_window
}


# ==========================================
# TOOLS DEFINITIONS 
# ==========================================

tools = [
    {
        "type": "function",
        "function": {
            "name": "manage_events",
            "description": "Create or edit an event",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "description": {"type": "string"},
                    "action": {"type": "integer"}
                },
                "required": ["date", "time", "description", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_events",
            "description": "Show future events",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit":{"type": "integer", "description": "Max amount of future event to show"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "home_assistant",
            "description": "show status of home devices and change their status",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_input": {  
                        "type": "string",
                        "description": "ID o nome del device"
                    },
                    "action": {"type": "integer", "description": "0=stato,1=accendi,2=spegni"}
                },
                "required": ["device_input", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop",
            "description": "Call this function if the user wants you to stop talking, be quiet, or cancel the current operation. Do not provide a text response after calling this.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "timer",
            "description": "Call this function to set allarms and timers",
            "parameters": {
                "type": "object",
                "properties": {
                    "name":{
                        "type": "string",
                        "description": "The name of the timer or of the allarm"
                    },
                    "time": {
                        "type": "string",
                        "description": "The provided time represents the exact moment when the alarm or timer must trigger, calculated based on the known start time and the specified end time or duration. The output format must be H:M:S."
                    },
                    "tipe":{
                        "type": "integer",
                        "description": " Timer=0, alram =1"
                    }                    
                },
                "required": ["time", "tipe"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_music",
            "description": "Manages music playback via subsonic, if the user what to do an action like next song, previous song, play or pause use this words as action parameter, otherside use 0", 
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {            
                        "type": "string",
                        "description": "Action to perform, you must follow MANAGE_MUSIC rules"
                    },
                    "song_name": {
                        "type": "string",
                        "description": "The title of the requested song, artist, or playlist. If the tool returns a list of items instead of playing, analyze the list considering possible speech-to-text spelling errors, then call this tool AGAIN with the EXACT name of the best match. If none are similar, call it with 'random'."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_volume",
            "description": "Manages volume, increes, decress and set a specific volume.", 
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {            
                        "type": "string",
                        "description": "Action to perform, you must follow MANAGE_VOLUME rules"
                    },
                    "volume": {
                        "type": "integer",
                        "description": "Return only an integer representing the volume change or target volume: if the user specifies increasing or decreasing by a certain amount, output that amount; if the user specifies setting the volume to a specific value, output that value; if no amount or value is specified, return nothing."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bluetooth_actions",
            "description": "Connects or disconnects a paired Bluetooth device (like speakers, headphones, phones).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "'connect' to connect a device, 'disconnect' to disconnect."
                    },
                    "device_name": {
                        "type": "string",
                        "description": "You must follow BLUETOOTH_ACTIONS rules."
                    }
                },
                "required": ["action", "device_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_window",
            "description": "Open system windows, like options and bluetooth settings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window": {
                        "type": "string",
                        "description": """The name of the window the user want to open. You must return one of those options:
                            Command format: [window code] = [Window descriptio]
                            1. settings = OpenHUB settings.
                            2. bluetooth = Bluethoo settings
                        if you don't know what window the user asked pass window as None.
                        """
                    },
                
                },
                "required": ["window"]
            }
        }
    },
]