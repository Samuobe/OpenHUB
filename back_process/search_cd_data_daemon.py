import subprocess
import time
import discid
import musicbrainzngs
from pydub import AudioSegment
from mutagen.id3 import ID3, TIT2, TPE1, TALB, ID3NoHeaderError
from python_mpv_jsonipc import MPV

DEVICE = "/dev/sr0"
OUTPUT = "/tmp/fake_track.mp3"

musicbrainzngs.set_useragent("OpenHUB-CD-Module", "1.1", "https://github.com/samuobe/OpenHUB")

def init_mpv():
    try:
        return MPV()
    except:
        return None


mpv_player = None

def is_cd_inserted():
    try:
        discid.read(DEVICE)
        return True
    except:
        return False


def get_cd_id():
    try:
        return discid.read(DEVICE).id
    except:
        return None

def vlc_has_metadata():
    try:
        out = subprocess.check_output(
            ["playerctl", "-p", "vlc", "metadata"],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        if (
            "xesam:title" not in out
            or "xesam:artist" not in out
            or "xesam:album" not in out
        ):
            return False

        meta = {}
        for line in out.splitlines():
            parts = line.split(maxsplit=2)
            if len(parts) >= 3:
                key = parts[1]
                val = parts[2].strip().lower()
                # Rimuove apici singoli o doppi se presenti
                if (val.startswith("'") and val.endswith("'")) or (
                    val.startswith('"') and val.endswith('"')
                ):
                    val = val[1:-1]
                meta[key] = val

        title = meta.get("xesam:title", "")
        artist = meta.get("xesam:artist", "")
        album = meta.get("xesam:album", "")

        if title.startswith("track ") or title.startswith("traccia "):
            return False

        if artist in ["unknown artist", "artista sconosciuto", "unknown"]:
            return False

        if album in ["audio cd", "cd audio", "unknown"]:
            return False

        return True

    except:
        return False

def get_vlc_track_number():
    try:
        out = subprocess.check_output(
            ["playerctl", "-p", "vlc", "metadata"],
            text=True,
            stderr=subprocess.DEVNULL
        )

        for line in out.splitlines():
            if "xesam:tracknumber" in line:
                return int(line.split()[-1])

    except:
        pass

    return 1


def get_track_metadata(disc_id, track_number):
    try:
        result = musicbrainzngs.get_releases_by_discid(
            disc_id,
            includes=["artists", "recordings"]
        )

        release = result['disc']['release-list'][0]

        album = release.get("title", "Audio CD")
        artist = release.get("artist-credit-phrase", "Unknown Artist")

        idx = track_number - 1

        try:
            tracks = release['medium-list'][0]['track-list']
            title = tracks[idx]['recording']['title'] if idx < len(tracks) else f"Track {track_number}"
        except:
            title = f"Track {track_number}"

        return title, artist, album

    except:
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

    if not mpv_player:
        mpv_player = init_mpv()

    if mpv_player:
        mpv_player.loadfile(OUTPUT, "replace")
        time.sleep(0.2)
        mpv_player.command("seek", 0, "absolute")



last_track = -1
last_disc = None
is_active = False

while True:
    if is_cd_inserted():
        is_active = True
        disc_id = get_cd_id()

        if disc_id != last_disc:
            time.sleep(2.5)

        track = get_vlc_track_number()

        if disc_id != last_disc or track != last_track:

            players = subprocess.check_output(
                ["playerctl", "-l"], text=True, stderr=subprocess.DEVNULL
            ).splitlines()

            vlc_present = "vlc" in players
            vlc_has_data = vlc_has_metadata()

            if vlc_present and vlc_has_data:
                try:
                    if mpv_player:
                        mpv_player.command("stop")
                        mpv_player = None
                except:
                    mpv_player = None

            else:
                title, artist, album = get_track_metadata(disc_id, track)
                write_and_load(title, artist, album)

            last_disc = disc_id
            last_track = track

    else:
        if is_active:
            try:
                if mpv_player:
                    mpv_player.command("stop")
            except:
                pass

            mpv_player = None
            last_disc = None
            last_track = -1
            is_active = False

    time.sleep(1)