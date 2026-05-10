import time
import threading
import discid
import musicbrainzngs
from pydbus import SessionBus
from gi.repository import GLib
from mpris_server.server import Server
from mpris_server.adapters import MprisAdapter
from mpris_server.base import URI


CD_DEVICE = "/dev/sr0"

musicbrainzngs.set_useragent(
    "OpenHUB",
    "1.0",
    "https://github.com/samuobe/OpenHUB"
)


class VLCReader:
    def __init__(self):
        self.bus = SessionBus()
        self.player = None

    def connect(self):
        try:
            self.player = self.bus.get(
                "org.mpris.MediaPlayer2.vlc",
                "/org/mpris/MediaPlayer2"
            )
            return True
        except Exception:
            self.player = None
            return False

    def get_metadata(self):
        try:
            return self.player.Player.Metadata
        except Exception:
            return {}

    def get_playback_status(self):
        try:
            return self.player.Player.PlaybackStatus
        except Exception:
            return "Stopped"

    def get_position(self):
        try:
            return self.player.Player.Position
        except Exception:
            return 0

    def next(self):
        try:
            self.player.Player.Next()
        except Exception:
            pass

    def previous(self):
        try:
            self.player.Player.Previous()
        except Exception:
            pass

    def play_pause(self):
        try:
            self.player.Player.PlayPause()
        except Exception:
            pass


class CDMetadata:
    def __init__(self):
        self.album = "Unknown Album"
        self.artist = "Unknown Artist"
        self.tracks = {}

    def load(self):
        try:
            disc = discid.read(CD_DEVICE)

            result = musicbrainzngs.get_releases_by_discid(
                disc.id,
                includes=["artists", "recordings"]
            )

            disc_data = result["disc"]

            if "release-list" not in disc_data:
                print("No MusicBrainz data found")
                return False

            release = disc_data["release-list"][0]

            self.album = release["title"]

            if "artist-credit-phrase" in release:
                self.artist = release["artist-credit-phrase"]

            medium = release["medium-list"][0]

            for track in medium["track-list"]:
                num = int(track["position"])

                title = track["recording"]["title"]

                length = int(track.get("length", 0))

                self.tracks[num] = {
                    "title": title,
                    "length": length,
                }

            print(f"Loaded album: {self.album}")
            return True

        except Exception as e:
            print("MusicBrainz error:", e)
            return False


class CDAdapter(MprisAdapter):
    def __init__(self, vlc_reader, cdmeta):
        super().__init__()

        self.vlc = vlc_reader
        self.cdmeta = cdmeta

        self.current_metadata = {}

    @property
    def metadata(self):
        return self.current_metadata

    @property
    def playback_status(self):
        return self.vlc.get_playback_status()

    @property
    def position(self):
        return self.vlc.get_position()

    def next(self):
        self.vlc.next()

    def previous(self):
        self.vlc.previous()

    def play(self):
        self.vlc.play_pause()

    def pause(self):
        self.vlc.play_pause()

    def play_pause(self):
        self.vlc.play_pause()

    @property
    def can_go_next(self):
        return True

    @property
    def can_go_previous(self):
        return True

    @property
    def can_play(self):
        return True

    @property
    def can_pause(self):
        return True

    @property
    def can_control(self):
        return True


class CDMPRISDaemon:
    def __init__(self):
        self.vlc = VLCReader()
        self.cdmeta = CDMetadata()

        self.adapter = CDAdapter(self.vlc, self.cdmeta)

        self.server = Server(
            "mycdplayer",
            adapter=self.adapter
        )

        self.last_track = None

    def extract_track_number(self, metadata):
        try:
            if "xesam:trackNumber" in metadata:
                return int(metadata["xesam:trackNumber"])

            if "vlc:track_number" in metadata:
                return int(metadata["vlc:track_number"])

        except Exception:
            pass

        return None

    def update_loop(self):
        while True:

            if self.vlc.player is None:
                print("Connecting to VLC...")
                self.vlc.connect()

            metadata = self.vlc.get_metadata()

            track_num = self.extract_track_number(metadata)

            if track_num != self.last_track and track_num is not None:

                self.last_track = track_num

                print("Track changed:", track_num)

                if track_num in self.cdmeta.tracks:

                    track = self.cdmeta.tracks[track_num]

                    self.adapter.current_metadata = {
                        "mpris:trackid": URI(f"/track/{track_num}"),
                        "xesam:title": track["title"],
                        "xesam:album": self.cdmeta.album,
                        "xesam:artist": [self.cdmeta.artist],
                        "xesam:trackNumber": track_num,
                        "mpris:length": track["length"] * 1000,
                    }

                    self.server.emit_properties_changed()

                    print("Updated MPRIS metadata")

            time.sleep(1)

    def run(self):

        print("Loading CD metadata...")

        self.cdmeta.load()

        thread = threading.Thread(
            target=self.update_loop,
            daemon=True
        )

        thread.start()

        print("Starting MPRIS server...")

        loop = GLib.MainLoop()
        loop.run()


if __name__ == "__main__":
    daemon = CDMPRISDaemon()
    daemon.run()