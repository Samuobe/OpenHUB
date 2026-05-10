#!/usr/bin/env python3

import time
import threading
import discid
import musicbrainzngs

from gi.repository import GLib
from pydbus import SessionBus
from mpris_server.server import Server
from mpris_server.adapters import MprisAdapter
from mpris_server.base import URI

CD_DEVICE = "/dev/sr0"

musicbrainzngs.set_useragent(
    "CDMetadataBridge",
    "1.0",
    "you@example.com"
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

    def metadata(self):
        if not self.player:
            return {}
        try:
            return self.player.Player.Metadata
        except Exception:
            return {}

    def playback_status(self):
        if not self.player:
            return "Stopped"
        try:
            return self.player.Player.PlaybackStatus
        except Exception:
            return "Stopped"

class CDDatabase:
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

            disc_data = result.get("disc", {})
            releases = disc_data.get("release-list", [])

            if not releases:
                print("No MusicBrainz match")
                return False

            release = releases[0]

            self.album = release.get("title", "Unknown Album")

            if "artist-credit-phrase" in release:
                self.artist = release["artist-credit-phrase"]

            medium = release["medium-list"][0]

            for track in medium["track-list"]:
                num = int(track["position"])
                title = track["recording"]["title"]
                length = int(track.get("length", 0))

                self.tracks[num] = {
                    "title": title,
                    "length": length
                }

            print(f"Loaded album: {self.album}")
            return True

        except Exception as e:
            print("MusicBrainz error:", e)
            return False


class CDAdapter(MprisAdapter):
    def __init__(self):
        super().__init__()
        self._metadata = {}

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value

    @property
    def playback_status(self):
        return "Playing"

    def next(self):
        pass

    def previous(self):
        pass

    def play(self):
        pass

    def pause(self):
        pass

    def play_pause(self):
        pass

    @property
    def can_control(self):
        return True

    @property
    def can_play(self):
        return True

    @property
    def can_pause(self):
        return True

    @property
    def can_go_next(self):
        return True

    @property
    def can_go_previous(self):
        return True


class CDDaemon:
    def __init__(self):
        self.vlc = VLCReader()
        self.cd = CDDatabase()

        self.adapter = CDAdapter()

        self.server = Server(
            "mycdplayer",
            adapter=self.adapter,
            bus_name="org.mpris.MediaPlayer2.mycdplayer"
        )

        self.last_track = None

    def extract_track(self, metadata):
        try:
            if "xesam:trackNumber" in metadata:
                return int(metadata["xesam:trackNumber"])
        except Exception:
            pass
        return None

    def update_loop(self):
        while True:

            if not self.vlc.player:
                print("Connecting to VLC...")
                self.vlc.connect()

            meta = self.vlc.metadata()
            track = self.extract_track(meta)

            if track and track != self.last_track:
                self.last_track = track

                if track in self.cd.tracks:

                    t = self.cd.tracks[track]

                    self.adapter.metadata = {
                        "mpris:trackid": URI(f"/track/{track}"),
                        "xesam:title": t["title"],
                        "xesam:album": self.cd.album,
                        "xesam:artist": [self.cd.artist],
                        "xesam:trackNumber": track,
                        "mpris:length": t["length"] * 1000,
                    }

                    print(f"Updated track: {t['title']}")

            time.sleep(0.5)

    def run(self):

        print("Loading CD metadata...")

        self.cd.load()

        print("Starting MPRIS server...")

        self.server.publish()   # 🔥 CRUCIALE

        threading.Thread(
            target=self.update_loop,
            daemon=True
        ).start()

        GLib.MainLoop().run()

if __name__ == "__main__":
    CDDaemon().run()