#!/usr/bin/env python3

import asyncio
import subprocess
import time
import discid
import musicbrainzngs
import os

# Configurazione
CD_DEVICE = "/dev/sr0"
musicbrainzngs.set_useragent("CDMetadataBridge", "1.6", "your-email@example.com")

class CDDaemon:
    def __init__(self):
        self.album_info = {"title": "CD Audio", "artist": "Sconosciuto", "tracks": {}}
        self.mpv_process = None

    def load_cd(self):
        try:
            print(f"Lettura disco: {CD_DEVICE}")
            disc = discid.read(CD_DEVICE)
            res = musicbrainzngs.get_releases_by_discid(disc.id, includes=["artists", "recordings"])
            if "disc" in res and "release-list" in res["disc"]:
                rel = res["disc"]["release-list"][0]
                self.album_info["title"] = rel.get("title", "Unknown Album")
                self.album_info["artist"] = rel.get("artist-credit-phrase", "Unknown Artist")
                medium = rel["medium-list"][0]
                for track in medium["track-list"]:
                    num = int(track["position"])
                    self.album_info["tracks"][num] = {
                        "title": track["recording"]["title"],
                        "length": int(track.get("length", 0))
                    }
                print(f"CD Caricato: {self.album_info['title']} - {self.album_info['artist']}")
            else:
                self._load_defaults()
        except Exception as e:
            print(f"Errore CD: {e}")
            self._load_defaults()

    def _load_defaults(self):
        self.album_info["title"] = "CD Audio"
        self.album_info["artist"] = "Sconosciuto"
        for i in range(1, 16):
            self.album_info["tracks"][i] = {"title": f"Traccia {i}", "length": 180000}

    def start_ghost_player(self):
        print("Avvio del Ghost Player (mpv)...")
        # Aggiungiamo --no-audio per non sentire il silenzio di 1 secondo
        cmd = ["mpv", "--idle", "--no-video", "--no-audio", "--input-ipc-server=/tmp/mpvsocket"]
        self.mpv_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)

    def create_tagged_file(self, track_num):
        t = self.album_info["tracks"][track_num]
        title = t["title"]
        artist = self.album_info["artist"]
        album = self.album_info["title"]
        filename = f"/tmp/track_{track_num}.mp3"

        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "1", 
            "-metadata", f"title={title}",
            "-metadata", f"artist={artist}",
            "-metadata", f"album={album}",
            filename
        ]
        
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return filename
        except Exception as e:
            print(f"Errore creazione file: {e}")
            return None

    def update_mpris_via_bash(self, track_num):
        if track_num not in self.album_info["tracks"]:
            return

        filename = self.create_tagged_file(track_num)
        if not filename:
            return

        # SEQUENZA COMANDI CRUCIALE:
        # 1. Carica il file
        # 2. Forza la riproduzione (Senza Play, i metadati non appaiono su MPRIS)
        # 3. Togli la pausa
        commands = [
            f"loadfile {filename} approx 0",
            "set pause no",
            "play"
        ]
        
        full_cmd = "\n".join(commands)
        
        try:
            # Usiamo socat per inviare i comandi
            subprocessC = f"echo '{full_cmd}' | socat - UNIX-CONNECT:/tmp/mpvsocket"
            subprocess.run(subprocessC, shell=True, stderr=subprocess.DEVNULL)
            print(f"MPRIS Update -> {self.album_info['artist']} - {self.album_info['title']} (Traccia {track_num})")
        except Exception as e:
            print(f"Errore comando bash: {e}")

    async def run(self):
        self.load_cd()
        self.start_ghost_player()
        
        track = 1
        try:
            while True:
                print(f"Simulando riproduzione Traccia {track}...")
                self.update_mpris_via_bash(track)
                
                # Attendi 30 secondi per lo scrobbling di ListenBrainz
                await asyncio.sleep(30)
                
                track = track + 1 if (track + 1) in self.album_info["tracks"] else 1
        except KeyboardInterrupt:
            print("\nSpegnimento...")
        finally:
            if self.mpv_process:
                self.mpv_process.terminate()

if __name__ == "__main__":
    daemon = CDDaemon()
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        pass