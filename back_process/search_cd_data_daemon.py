from pydub import AudioSegment
from mutagen.id3 import ID3, TIT2, TPE1, TALB, ID3NoHeaderError
from python_mpv_jsonipc import MPV
import time

OUTPUT = "/tmp/fake_track.mp3"

TITLE = "Numb"
ARTIST = "Linkin Park"
ALBUM = "Meteora"

AudioSegment.silent(duration=180000).export(OUTPUT, format="mp3")

try:
    tags = ID3(OUTPUT)
except ID3NoHeaderError:
    tags = ID3()

tags["TIT2"] = TIT2(encoding=3, text=TITLE)
tags["TPE1"] = TPE1(encoding=3, text=ARTIST)
tags["TALB"] = TALB(encoding=3, text=ALBUM)
tags.save(OUTPUT)

print("Fake MP3 creato")

mpv = MPV()
mpv.loadfile(OUTPUT, "replace")

time.sleep(1)

mpv.command("seek", 0, "absolute")

print("Playing")

while True:
    time.sleep(1)
