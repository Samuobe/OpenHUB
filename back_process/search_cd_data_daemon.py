from python_mpv_jsonipc import MPV
import time

FILE = "/home/samuobe/music/numb.mp3"

mpv = MPV()

print("Loading...")

# ✔ carica file
mpv.loadfile(FILE, "replace")

time.sleep(0.5)

# ✔ METADATA VISIBILE (modo corretto)
mpv.command("show-text", "Linkin Park - Numb", 3000)

# ✔ TITOLO FINESTRA (CORRETTO VIA PROPERTY DIRECTA)
mpv.force_media_title = "Linkin Park - Numb"

print("Playing single track")

while True:
    time.sleep(1)