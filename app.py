import os
from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRect, QProcess, QObject
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
import musicbrainzngs
import sys
import functions.lpak as lpak
import configparser
import functions.get_language_code as get_language_code

def test_mode_enable():    
    return os.path.isfile("test.txt")

data_path = ""

#load config
config =configparser.ConfigParser()
config.optionxform = str
config.read(f"{data_path}config.conf")
language = config.get("User data", "Language")
language_code = get_language_code.get(language)
screensaver_timeout = config.get("User data","Screensaver_timeout")

music_widget_status = config.get("Widgets", "Music")
calendar_widget_status = config.get("Widgets", "Calendar")
weather_widget_status = config.get("Widgets", "Weather")

#Load credential
config_credential =configparser.ConfigParser()
config_credential.optionxform = str
config_credential.read(f"{data_path}credential.env")
city = config_credential.get("Device info", "city")

def setting_status(a):
    if a=="Enable":
        return True
    else:
        return False

musicbrainzngs.set_useragent("OpenHUB", "0.1", "https://github.com/Samuobe/OpenHUB")

#global gabbage
active_player_name = None
last_title = ""
current_image_index = 0

#Threads
active_threads = []
current_cover_thread = None

app = QApplication(sys.argv)

# Start loading
screen = app.primaryScreen()
rect = screen.geometry()
pixmap = QPixmap(rect.width(), rect.height())
pixmap.fill(QColor("#000000")) 

painter = QPainter(pixmap)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)

painter.setBrush(QColor("#1a4d2e"))
painter.drawRect(0, 0, rect.width(), rect.height())

painter.setBrush(QColor("#2e7d32"))

central_rect = QRect(rect.width()//2 - 250, rect.height()//2 - 150, 500, 300)
painter.drawRoundedRect(central_rect, 30, 30)

painter.end()
splash = QSplashScreen(pixmap, Qt.WindowType.FramelessWindowHint | 
                               Qt.WindowType.WindowStaysOnTopHint | 
                               Qt.WindowType.Tool)

splash.setGeometry(rect)
if not test_mode_enable():
    splash.showFullScreen()
else:
    splash.show()
splash.raise_() 
splash.activateWindow()

splash.setFont(QFont("Ubuntu", 30, QFont.Weight.Bold))
splash.showMessage(f"OpenHUB\n{lpak.get("Loading", language)}...", 
                   Qt.AlignmentFlag.AlignCenter, 
                   Qt.GlobalColor.white)

app.processEvents()
#####################
#####################
######END#SPASH######
#####################
#####################






#LIBRERIE
import os
import re
import json
import glob
import time
import datetime
import subprocess
import importlib
import requests
import alsaaudio
from PyQt6.QtCore import (
    QTime, Qt, QTimer, QObject, QEvent,
    QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QHBoxLayout, QVBoxLayout, QGridLayout,
    QWidget, QLabel, QPushButton, QDialog, QScrollArea,
    QFrame, QMenu, QSlider, QStackedLayout,
    QGraphicsOpacityEffect, QSizePolicy
)
from Lattuga.lattuga import voice_input, Lattuga, manual_input
import Lattuga.tools as my_tools
from Lattuga.tools import get_events, get_weather
from functions.mpv_status import is_mpv_running
from other_windows.app_store import open_store_page
from other_windows.settings import open_settings_page
from other_windows.bluetooth_manager import open_bluetooth_window

style_widget = """
    QLabel {
        background-color:  #e6ffe6;
        color: black;
        border-radius: 15px;
        padding: 10px;
        font-size: 16px;
        font-size: 30;
    }
"""

if os.path.isfile(f"{data_path}conversation.json"):
    os.remove(f"{data_path}conversation.json")

def is_fake_mpv_running():
    try:
        players = subprocess.check_output(
            ["playerctl", "-l"],
            text=True,
            stderr=subprocess.DEVNULL
        ).splitlines()

        for p in players:
            if p.startswith("mpv.instance-"):
                return True
        
        return False

    except Exception:
        return False

def get_playing(player: str = None):
    def query(p, format_string="{{status}}|||{{xesam:artist}}|||{{xesam:title}}|||{{xesam:album}}|||{{playerName}}"):
        try:
            return subprocess.check_output(
                ["playerctl", "metadata", "-p", p, "--format", format_string],
                stderr=subprocess.DEVNULL, text=True, timeout=0.3
            ).strip()
        except:
            return None

    try:
        players = subprocess.check_output(["playerctl", "-l"], text=True, stderr=subprocess.DEVNULL).splitlines()
        
        # --- CASO CRITICO: CD IN CORSO (Fake MPV attivo) ---
        fake_mpv = next((p for p in players if p.startswith("mpv.instance-")), None)
        
        if fake_mpv:
            # 1. Prendiamo i METADATI dal fake MPV (Titolo, Artista, Album)
            meta_data = query(fake_mpv, "{{xesam:artist}}|||{{xesam:title}}|||{{xesam:album}}|||{{playerName}}")
            # 2. Prendiamo lo STATO reale da VLC (Playing/Paused)
            real_status = "paused"
            try:
                real_status = subprocess.check_output(
                    ["playerctl", "-p", "vlc", "status"], 
                    stderr=subprocess.DEVNULL, text=True
                ).strip().lower()
            except:
                pass
            
            if meta_data:
                # Ricostruiamo la stringa mettendo lo stato di VLC all'inizio
                return f"{real_status}|||{meta_data}"

        # --- CASO NORMALE: Altri player ---
        for p in ["mpv", "vlc"]: # Prova i player standard
            if p in players:
                res = query(p)
                if res: return res

        # Fallback sull'ultimo player rilevato
        for p in players:
            res = query(p)
            if res: return res

    except Exception:
        pass
    return None

def show_big_advice(testo):
    global current_popup, idle
    idle.reset()
    screensaver.hide()
    if current_popup:
        current_popup.close()

    popup = QDialog(root)
    current_popup = popup
    
    popup.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    screen_geometry = app.primaryScreen().geometry()
    
    popup.setGeometry(screen_geometry)

    layout_esterno = QVBoxLayout(popup)
    layout_esterno.setContentsMargins(0, 0, 0, 0) 
    layout_esterno.setAlignment(Qt.AlignmentFlag.AlignCenter) 

    main_frame = QFrame()
    main_frame.setFixedSize(int(screen_geometry.width() * 0.85), int(screen_geometry.height() * 0.75))
    main_frame.setStyleSheet("""
        QFrame {
            background-color: #1a4d2e; 
            border: 2px solid #e6ffe6; 
            border-radius: 40px;
        }
    """)
    
    layout_principale = QVBoxLayout(main_frame)
    layout_principale.setContentsMargins(40, 40, 40, 40)
    layout_esterno.addWidget(main_frame)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("background: transparent; border: none;")

    scroll.verticalScrollBar().setStyleSheet("""
        QScrollBar:vertical {
            border: none;
            background: #1a4d2e;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #e6ffe6;
            min-height: 20px;
            border-radius: 5px;
        }
    """)

    container_testo = QWidget()
    container_testo.setStyleSheet("background: transparent;")
    layout_testo = QVBoxLayout(container_testo)

    testo_pulito = re.sub(r'[\*\-_#]', '', testo)
    
    label = QLabel(testo_pulito)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    label.setStyleSheet("""
        color: #f0f0f0; 
        font-size: 20px; 
        font-family: 'Segoe UI', 'Ubuntu', sans-serif;
        line-height: 160%;
        background: transparent;
    """)
    
    layout_testo.addWidget(label)
    scroll.setWidget(container_testo)
    layout_principale.addWidget(scroll)

    btn_chiudi = QPushButton(lpak.get("Stop and return to the home page", language))
    btn_chiudi.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_chiudi.setStyleSheet("""
        QPushButton {
            background-color: #e6ffe6; 
            color: #1a4d2e; 
            font-weight: bold; 
            font-size: 16px;
            letter-spacing: 1px;
            height: 55px; 
            border-radius: 10px;
            margin-top: 20px;
            border: 2px solid white;
        }
        QPushButton:hover {
            background-color: #ffffff;
        }
        QPushButton:pressed {
            background-color: #c0dfc0;
        }
    """)
    
    btn_chiudi.clicked.connect(lambda: (tts.stop(), popup.close()))
    layout_principale.addWidget(btn_chiudi)

    tts.finished.connect(popup.close)
    
    popup.show()
        
    tts.say(testo_pulito)
    QTimer.singleShot(0, wait_keyword)

def clear_layout(layout, keep=1):
    while layout.count() > keep:
        item = layout.takeAt(keep)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()

##Screen saver
class IdleDetector(QObject):
    def __init__(self, timeout_ms, on_idle, on_resume):
        super().__init__()
        self.timeout_ms = timeout_ms
        self.on_idle = on_idle
        self.on_resume = on_resume

        self.timer = QTimer()
        self.timer.setInterval(timeout_ms)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.trigger_idle)

        self.active = True
        self.timer.start()

    def reset(self):
        if not self.active:
            self.on_resume()
            self.active = True
        self.timer.start()

    def trigger_idle(self):
        self.active = False
        self.on_idle()

class ActivityFilter(QObject):
    def __init__(self, idle_detector):
        super().__init__()
        self.idle_detector = idle_detector

    def eventFilter(self, obj, event):
        if event.type() in [
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel
        ]:
            self.idle_detector.reset()

            # se screensaver attivo → chiudi
            if screensaver.isVisible():
                screensaver.hide()

        return False

class ScreenSaver(QWidget):
    IMAGE_HEIGHT_RATIO = 0.78 #% space image in monitor
    SLIDE_MS = 5000 #photo timer
    FADE_MS = 800 #fade time
    MUSIC_POLL_MS = 2000 #update music timer

    def __init__(self, images_dir="custom/images/screensaver"):
        super().__init__()

        try_images = glob.glob("custom/images/immich/*")
        if try_images:
            images_dir = "custom/images/immich"


        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setStyleSheet("background-color: black;")

        self.image_container = QWidget(self)
        self.stack = QStackedLayout(self.image_container)
        self.stack.setContentsMargins(0, 0, 0, 0)

        self.img_a = QLabel()
        self.img_b = QLabel()
        for lab in (self.img_a, self.img_b):
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lab.setStyleSheet("background: transparent; color: white; font-size: 80px;")
            lab.setText("🌌")

        self.fx_a = QGraphicsOpacityEffect(self.img_a)
        self.fx_b = QGraphicsOpacityEffect(self.img_b)
        self.img_a.setGraphicsEffect(self.fx_a)
        self.img_b.setGraphicsEffect(self.fx_b)
        self.fx_a.setOpacity(1.0)
        self.fx_b.setOpacity(0.0)

        self.stack.addWidget(self.img_a)
        self.stack.addWidget(self.img_b)

        self.music_label = QLabel(self)
        self.music_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.music_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 160);
                color: white;
                padding: 10px 20px;
                font-size: 18px;
                border-top: 1px solid rgba(255,255,255,40);
            }
        """)
        self.music_label.setText("")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.image_container, stretch=1)
        layout.addWidget(self.music_label, stretch=0)

        exts = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp")
        self.images = []
        for ext in exts:
            self.images += glob.glob(os.path.join(images_dir, ext))
        self.images.sort()
        self.index = 0

        self.front_label = self.img_a
        self.back_label = self.img_b
        self.front_fx = self.fx_a
        self.back_fx = self.fx_b

        self.anim_in = QPropertyAnimation(self.back_fx, b"opacity", self)
        self.anim_out = QPropertyAnimation(self.front_fx, b"opacity", self)
        for a in (self.anim_in, self.anim_out):
            a.setDuration(self.FADE_MS)
            a.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(self.SLIDE_MS)

        self.music_timer = QTimer(self)
        self.music_timer.timeout.connect(self.update_now_playing)
        self.music_timer.start(self.MUSIC_POLL_MS)

        self._set_label_pix(self.front_label, self._get_current_pixmap_or_none())
        self.front_fx.setOpacity(1.0)
        self.back_fx.setOpacity(0.0)
        self.update_now_playing()

    def _scaled(self, pix: QPixmap) -> QPixmap:
        target_h = int(self.height() * self.IMAGE_HEIGHT_RATIO)
        return pix.scaledToHeight(target_h, Qt.TransformationMode.SmoothTransformation)

    def _get_current_pixmap_or_none(self):
        if not self.images:
            return None
        path = self.images[self.index]
        self.index = (self.index + 1) % len(self.images)
        pix = QPixmap(path)
        return None if pix.isNull() else pix

    def _set_label_pix(self, label: QLabel, pix: QPixmap | None):
        if pix is None:
            label.setPixmap(QPixmap())
            label.setText("🌌")
            return
        label.setText("")
        label.setPixmap(self._scaled(pix))

    def next_frame(self):
        pix = self._get_current_pixmap_or_none()
        self._set_label_pix(self.back_label, pix)

        self.back_fx.setOpacity(0.0)
        self.front_fx.setOpacity(1.0)

        self.anim_in.stop()
        self.anim_out.stop()

        self.anim_in = QPropertyAnimation(self.back_fx, b"opacity", self)
        self.anim_out = QPropertyAnimation(self.front_fx, b"opacity", self)
        for a in (self.anim_in, self.anim_out):
            a.setDuration(self.FADE_MS)
            a.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)

        self.anim_in.start()
        self.anim_out.start()

        self.front_label, self.back_label = self.back_label, self.front_label
        self.front_fx, self.back_fx = self.back_fx, self.front_fx

    def resizeEvent(self, event):
        super().resizeEvent(event)
        pix = self.front_label.pixmap()
        if pix and not pix.isNull():
            self.front_label.setPixmap(pix.scaledToHeight(
                int(self.height() * self.IMAGE_HEIGHT_RATIO),
                Qt.TransformationMode.SmoothTransformation
            ))

    def update_now_playing(self):
        raw = get_playing()
        if raw == None:
            self.music_label.setText(lpak.get("Nothing playing", language))
            return

        parts = raw.split("|||")
        if len(parts) < 5:
            self.music_label.setText(lpak.get("Nothing playing", language))
            return

        status, artist, title, album, player = [p.strip() for p in parts]
        if not title:
            self.music_label.setText(lpak.get("Nothing playing", language))
            return

        artist = artist or "Unknown artist"
        album_part = f" ({album})" if album else ""
        #self.music_label.setText(f"{status} • {artist} - {title}{album_part}  [{player}]")
        self.music_label.setText(f"{lpak.get(status.capitalize(), language)} • {artist} - {title}{album_part}")


#End screen saver

class CalendarWorker(QThread):
    finished = pyqtSignal(object) 

    def run(self):
        try:
            eventi = get_events() 
            self.finished.emit(eventi)
        except Exception as e:
            self.finished.emit(f"Calendar load error: {e}")

class KeywordWorker(QThread):
    finished = pyqtSignal(bool)

    def run(self):
        try:
            from Lattuga.lattuga import listen_for_keyword
            found = listen_for_keyword()
            self.finished.emit(found)
        except Exception as e:
            print(f"Error KeywordWorker: {e}")
            self.finished.emit(False)

class CoverWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, artist, album, title):
        super().__init__()
        if album == "":
            return
        self.artist = artist
        self.album = album
        self.title = title

    def run(self):
        try:
            search_query = self.album if self.album and len(self.album) > 2 else self.title
            result = musicbrainzngs.search_releases(artist=self.artist, release=search_query, limit=1)
            
            if result['release-list']:
                release_id = result['release-list'][0]['id']
                url = f"https://coverartarchive.org/release/{release_id}/front"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    self.finished.emit(response.content) 
                    return
            
            self.finished.emit(None)
        except Exception as e:
            print(f"Cover error: {e}")
            self.finished.emit(None)

class VoiceWorker(QThread):
    global idle
    finished = pyqtSignal(str)
    wake = pyqtSignal()
    def run(self):
        self.wake.emit()
        try:            
            prompt = voice_input(turn_down_volume=True)
            self.finished.emit(prompt if prompt else "")            
        except:
            screensaver.hide()
            status_label.setText("Error, microphone not found!!")


class AIWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        response = Lattuga(self.prompt)
        self.finished.emit(response)

class TTSManager(QObject):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.process = QProcess()
        self.process.finished.connect(self._handle_process_finished)
        self.last_music_status = ""

    def _handle_process_finished(self):
        if "playing" in self.last_music_status:
            print("*** Restarting music...")
            if is_mpv_running():
                os.system('playerctl -p "mpv" play')
            else:
                os.system("playerctl play")
            self.last_music_status = "paused"
        self.finished.emit() 

    def say(self, text):
        try:
            if is_mpv_running():
                status = os.popen('playerctl -p "mpv" status').read().strip().lower()
            else:
                status = os.popen('playerctl status').read().strip().lower()
            if "playing" in status:
                self.last_music_status = "playing"
                if is_mpv_running():
                    os.system('playerctl -p "mpv" pause')
                else:
                    os.system("playerctl pause")
            else:
                self.last_music_status = "stopped"
        except:
            self.last_music_status = "stopped"

        self.stop_process_only() 
        
        clean_text = re.sub(r'[^\w\s,.?]', '', text)
        if clean_text.strip():
            self.process.start("espeak-ng", ["-v", language_code, "-a", "100", clean_text])
        else:
            self._handle_process_finished()

    def stop_process_only(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
            self.process.waitForFinished(500)

    def stop(self):
        self.stop_process_only()

tts = TTSManager()
current_popup = None

def verify_actions(response):
    if my_tools.window_to_open == "settings":
        open_settings_page()
        my_tools.window_to_open = None 
    elif my_tools.window_to_open == "bluetooth":
        open_bluetooth_window()
        my_tools.window_to_open = None
    return response

def ask_ai():
    global voice_worker

    idle.reset()
    if screensaver.isVisible():
        screensaver.hide()

    if 'voice_worker' in globals() and voice_worker is not None and voice_worker.isRunning():
        print("DEBUG: voice_worker is already running!")
        return

    tts.stop()
    if current_popup:
        current_popup.close()
        
    status_label.setText(f"🎤 {lpak.get("Listening", language)}...")
    
    voice_worker = VoiceWorker()

    def handle_voice_result(prompt):
        if not prompt:
            status_label.setText(f"❓ {lpak.get("I didn't catch that", language)}, {lpak.get("Could you repeat it?", language).lower()}")
            QTimer.singleShot(2000, wait_keyword)
            return

        status_label.setText(f"🧠 {lpak.get("I'm thinking", language)}...")
        
        global ai_worker
        prompt = prompt + "\nThis request is from "+device_name
        ai_worker = AIWorker(prompt)
        
        def handle_ai_result(response):
            
            response = verify_actions(response)
            
            response = response.replace("*", "").replace("\n", " ")
            if len(response) < 200:
                status_label.setText(response)
                tts.say(response)
            else:
                status_label.setText(f"✅ {lpak.get('Answer provided', language)}")
                show_big_advice(response) 
            
            def restart():
                QTimer.singleShot(1000, wait_keyword)
            
            try:
                tts.finished.disconnect()
            except:
                pass

            tts.finished.connect(restart)

        ai_worker.finished.connect(handle_ai_result)
        ai_worker.start()

    voice_worker.finished.connect(handle_voice_result)
    voice_worker.start()

keyword_thread = None 

def manage_keyword_result(trovata):
    global keyword_thread

    if not trovata:
        QTimer.singleShot(1000, wait_keyword)
        return

    idle.reset()
    if screensaver.isVisible():
        screensaver.hide()

    if keyword_thread:
        keyword_thread.finished.disconnect()

    status_label.setStyleSheet("color: green; font-weight: bold;")
    ask_ai()

def wait_keyword():
    global keyword_thread

    if keyword_thread is not None and keyword_thread.isRunning():
        print("DEBUG: KeywordWorker already activated, ingoring request.")
        return

    status_label.setText(f"{lpak.get("Waiting for orders", language)}. {lpak.get('Say "Hey Jarvis"', language)}")
    status_label.setStyleSheet("color: black;") 
    
    keyword_thread = KeywordWorker()
    keyword_thread.finished.connect(manage_keyword_result)
    keyword_thread.start()

#UPDATE GUI

def update_time():
    time_now = datetime.datetime.now().strftime("%H:%M \n %d/%m/%Y")
    label_time.setText(time_now)

last_title = ""
last_album_artist = ""
current_cover_thread = None

def update_music():
    global last_title, last_album_artist, current_cover_thread
    global music_artist, music_title, music_album, music_play_button, music_cover_label

    def set_cover_or_emoji(result=None, loading=False):
        music_cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if result:
            pixmap = QPixmap()
            pixmap.loadFromData(result)
            music_cover_label.setPixmap(pixmap)
            music_cover_label.setText("")
            music_cover_label.setStyleSheet("border-radius: 10px;") 
        else:
            music_cover_label.setPixmap(QPixmap())
            music_cover_label.setText("⏳" if loading else "🎵")
            music_cover_label.setStyleSheet("""
                background-color: #ddd;
                border-radius: 10px;
                font-size: 70px;
            """)

    try:         
        music_data_raw = get_playing()

        if not music_data_raw:
            if last_title != "": 
                music_title.setText(lpak.get("Nothing is playing", language))
                music_artist.setText("")
                music_album.setText("")
                last_title = ""
                last_album_artist = ""
                set_cover_or_emoji(None)
            return

        parts = music_data_raw.strip().split("|||")
        if len(parts) < 5:
            return

        status, artist, title, album, player = parts

        if title != last_title:
            last_title = title
            music_artist.setText(f"{lpak.get('Artist', language)}: {artist}")
            if not "stream.view?" in title:
                music_title.setText(f"{lpak.get('Title', language)}: {title}")
            else:
                music_title.setText(f"{lpak.get('Loading', language)}...")

            music_album.setText(f"{lpak.get('Album', language)}: {album}")

        current_album_artist = f"{artist}|||{album}"
        if current_album_artist != last_album_artist:
            last_album_artist = current_album_artist
            if current_cover_thread:
                try:
                    current_cover_thread.finished.disconnect()
                except:
                    pass

            set_cover_or_emoji(None, loading=True)

            current_cover_thread = CoverWorker(artist, album, title)
            
            def on_finished(result, thread_ref=current_cover_thread):
                if thread_ref == current_cover_thread:
                    set_cover_or_emoji(result)
                if thread_ref in active_threads:
                    active_threads.remove(thread_ref)

            current_cover_thread.finished.connect(on_finished)
            active_threads.append(current_cover_thread)
            current_cover_thread.start()

        if status.lower() == "playing":
            music_play_button.setText("⏸️")
        else:
            music_play_button.setText("▶️")
      
    except Exception:
        music_title.setText(lpak.get("Nothing is playing", language))
        music_artist.setText("")
        music_album.setText("")
        last_title = ""
        last_album_artist = ""
        set_cover_or_emoji(None)
        pass

def update_gui():
    update_time()
    if setting_status(music_widget_status):
        update_music()
    #root.repaint()


#LONG
def load_calendar():
    global calendar_thread   
    global calendar_container, calendar_layout, title_event_label

    clear_layout(calendar_layout, 1)

    title_event_label.setText(f"📅 {lpak.get("Loading calendar", language)}...") 
    
    calendar_thread = CalendarWorker()
    
    def on_events_loaded(events):
        title_event_label.setText("📅 "+lpak.get("Calendar", language).upper())
        
        if isinstance(events, str):
            event_label = QLabel(text=events)
            calendar_layout.addWidget(event_label, 1, 0, 1, 2)
            return

        r = 1
        event_n = 0
        for event in events:
            if event_n > 5:
                break
            event_n += 1
            
            event_parts = event.split(" | ")
            if len(event_parts) == 2:
                name = event_parts[0]
                date = event_parts[1]
                point = "✴️"            
                event_text = f"{point} {name}"
                
                if " " in date:
                    time = date.split(" ")[1]
                    date = date.split(" ")[0]      
                    date_event_text = f"{date} {time}" 
                else:               
                    date_event_text = f"{date} {lpak.get("All day", language)}"

                event_label = QLabel(text=event_text)
                date_event_label = QLabel(text=date_event_text)
                calendar_layout.addWidget(event_label, r, 0)
                calendar_layout.addWidget(date_event_label, r, 1)
                r += 1

    calendar_thread.finished.connect(on_events_loaded)
    calendar_thread.start()

def long_update_widget():
    print("Update lungo")
    if setting_status(calendar_widget_status):
        load_calendar()

def load_static_data():
    print("No static data for now!")

def first_load():
    load_static_data()
    load_calendar()

#Other update
def update_imagesFrame():
    global current_image_index

    import glob, random
    from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
    from PyQt6.QtGui import QPixmap

    images = glob.glob("custom/images/immich/*")

    if not images:
        image_label.setWordWrap(True)
        image_label.setText(
            f"{lpak.get('No images, please log in with Immich and create an album called OpenHUB', language)}. "
            f"{lpak.get('See the wiki on GitHub for more informations', language)}."
        )
        return

    if current_image_index >= len(images):
        current_image_index = 0

    path = images[current_image_index]
    current_image_index += 1

    pixmap = QPixmap(path)
    if pixmap.isNull():
        return

    scaled = pixmap.scaled(
        image_label.size(),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    opacity = image_label._opacity

    fade_out = QPropertyAnimation(opacity, b"opacity")
    fade_out.setDuration(200)
    fade_out.setStartValue(1.0)
    fade_out.setEndValue(0.0)

    def swap_image():
        image_label.setPixmap(scaled)

        fade_in = QPropertyAnimation(opacity, b"opacity")
        fade_in.setDuration(400)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        fade_in.start()
        image_label._anim_in = fade_in

    fade_out.finished.connect(swap_image)
    fade_out.start()

    image_label._anim_out = fade_out


mixer = alsaaudio.Mixer()

config.read("credential.env")
device_name = config.get("Device info", "device_name")


#CONFIG
def verify_folders():
    folders = ["data"]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)


def config_initial_volume():
    global mixer
    if os.path.isfile("data/audio_volume.data"):
        with open("data/audio_volume.data", "r") as f:
            data = f.readlines()
            mixer.setvolume(int(data[0]))

    if os.path.isfile("data/mic_volume.data"):
        with open("data/mic_volume.data", "r") as f:
            data = f.readlines()

            result = subprocess.run(
                ["pactl", "get-default-source"],
                capture_output=True,
                text=True
            )
            source = result.stdout.strip()

            subprocess.run([
                "pactl",
                "set-source-volume",
                source,
                f"{int(data[0])}%"
            ])


verify_folders()
if not test_mode_enable():
    config_initial_volume()


#Prepare interface
root = QMainWindow()
root.setWindowTitle("OpenHUB")
screensaver = ScreenSaver()


central_widget = QWidget()
root.setCentralWidget(central_widget)
main_layout = QVBoxLayout(central_widget)

#Screem saver
def show_screensaver():
    if test_mode_enable():
        screensaver.showMaximized()
    else:
        screensaver.showFullScreen()
    screensaver.raise_()
    screensaver.activateWindow()

def hide_screensaver():
    screensaver.hide()
idle = IdleDetector(
    timeout_ms=int(screensaver_timeout), 
    on_idle=show_screensaver,
    on_resume=hide_screensaver
)
def wake_up():
    idle.reset()
    if screensaver.isVisible():
        screensaver.hide()
activity_filter = ActivityFilter(idle)
app.installEventFilter(activity_filter)

# up bar
def show_energy_popup():
    dialog = QDialog(root)
    
    dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    dialog.setModal(True)
    dialog.setFixedSize(350, 250)
    
    dialog.setStyleSheet("""
        QDialog {
            background-color: #ffffff;
            border-radius: 8px;
            border: 2px solid #0078D7; /* Aggiunto un bordino per farlo risaltare */
        }
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 8px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton#system {
            background-color: #ff4c4c;
            color: white;
            border: none;
        }
        QPushButton#system:hover {
            background-color: #e60000;
        }
    """)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(10)
    layout.setContentsMargins(10, 10, 10, 10)


    btn_shutdown = QPushButton(lpak.get("System power off", language))
    btn_shutdown.setObjectName("system")
    btn_restart = QPushButton(lpak.get("System reboot", language))
    btn_restart.setObjectName("system")
    btn_close = QPushButton(lpak.get("Close", language))
    btn_restart_openhub = QPushButton(lpak.get("Restart OpenHUB", language))
    btn_close_openhub = QPushButton(lpak.get("Close OpenHUB", language))

    btn_shutdown.clicked.connect(lambda: os.system("systemctl poweroff"))
    btn_restart.clicked.connect(lambda: os.system("systemctl reboot"))
    btn_close.clicked.connect(dialog.close)
    def close_openhub():
        os.system("systemctl --user stop openhub.service")
        exit()
    def restart_openhub():
        os.system("systemctl --user restart openhub.service ")
        exit()

    btn_close_openhub.clicked.connect(close_openhub)
    btn_restart_openhub.clicked.connect(restart_openhub)

    layout.addWidget(btn_restart_openhub)
    layout.addWidget(btn_close_openhub)
    layout.addWidget(btn_shutdown)
    layout.addWidget(btn_restart)
    layout.addWidget(btn_close)

    dialog.exec()

def show_volume_popup():
    #get mic data
    def get_default_source():
        result = subprocess.run(
            ["pactl", "get-default-source"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def get_source_volume(source):
        result = subprocess.run(
            ["pactl", "get-source-volume", source],
            capture_output=True,
            text=True
        )

        match = re.search(r"(\d+)%", result.stdout)
        return int(match.group(1)) if match else 0

    def set_mic_volume(source, volume):
        subprocess.run([
            "pactl",
            "set-source-volume",
            source,
            f"{volume}%"
        ])
        with open("data/mic_volume.data", "w") as f:
            f.write(str(volume))

    #get stereo data
    def set_stereo_volume(volume):
        mixer.setvolume(volume)
        with open("data/audio_volume.data", "w") as f:
            f.write(str(volume))


    #get data
    mic = get_default_source()
    mic_volume = get_source_volume(mic)

    stereo_volume= mixer.getvolume()[0]

    #interface
    dialog = QDialog(root)
    dialog.setWindowFlags(
        Qt.WindowType.FramelessWindowHint |
        Qt.WindowType.WindowStaysOnTopHint
    )
    dialog.setModal(True)
    dialog.setFixedSize(350, 180)

    dialog.setStyleSheet("""
        QDialog {
            background-color: #ffffff;
            border-radius: 10px;
            border: 2px solid #0078D7;
        }

        QLabel {
            color: black;
            font-size: 20px;
            font-weight: bold;
        }

        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 6px;
            padding: 6px;
            font-size: 16px;
        }

        QPushButton:hover {
            background-color: #e0e0e0;
        }

        QSlider::groove:horizontal {
            height: 6px;
            background: #ddd;
            border-radius: 3px;
        }

        QSlider::sub-page:horizontal {
            background: #0078D7;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            width: 14px;
            background: #0078D7;
            border-radius: 7px;
            margin: -5px 0;
        }
    """)

    layout = QVBoxLayout(dialog)

    #labels
    label_mic_volume = QLabel(f"{lpak.get("Microphone sensitivity", language)}: {mic_volume}%")
    label_mic_volume.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label_stereo_volume = QLabel(f"{lpak.get("Audio volume", language)}: {stereo_volume}%")
    label_stereo_volume.setAlignment(Qt.AlignmentFlag.AlignCenter)

    #mic slider
    mic_slider = QSlider(Qt.Orientation.Horizontal)
    mic_slider.setMinimum(0)
    mic_slider.setMaximum(100)
    mic_slider.setValue(mic_volume)

    #stereo slider
    stereo_slider = QSlider(Qt.Orientation.Horizontal)
    stereo_slider.setMinimum(0)
    stereo_slider.setMaximum(100)
    stereo_slider.setValue(stereo_volume)


    #Update funtions
    def update_mic_volume(value):
        label_mic_volume.setText(f"{lpak.get("Microphone sensitivity", language)}: {value}%")
        set_mic_volume(mic, value)

    def update_stereo_volume(value):
        label_stereo_volume.setText(f"{lpak.get("Audio volume", language)}: {value}%")
        set_stereo_volume(value)

    mic_slider.valueChanged.connect(update_mic_volume)
    stereo_slider.valueChanged.connect(update_stereo_volume)

    #Mic things
    btn_minus_mic = QPushButton("➖")
    btn_plus_mic = QPushButton("➕")

    def change_mic(delta):
        new_value = mic_slider.value() + delta
        new_value = max(0, min(100, new_value))
        mic_slider.setValue(new_value)

    btn_minus_mic.clicked.connect(lambda: change_mic(-1))
    btn_plus_mic.clicked.connect(lambda: change_mic(1))

    #Stereo things
    btn_minus_stereo = QPushButton("➖")
    btn_plus_stereo = QPushButton("➕")

    def change_stereo(delta):
        new_value = stereo_slider.value() + delta
        new_value = max(0, min(100, new_value))
        stereo_slider.setValue(new_value)

    btn_minus_stereo.clicked.connect(lambda: change_stereo(-5))
    btn_plus_stereo.clicked.connect(lambda: change_stereo(5))

    #mic control
    hbox_mic = QHBoxLayout()
    hbox_mic.addWidget(btn_minus_mic)
    hbox_mic.addWidget(mic_slider)
    hbox_mic.addWidget(btn_plus_mic)

    #volume control
    hbox_stereo = QHBoxLayout()
    hbox_stereo.addWidget(btn_minus_stereo)
    hbox_stereo.addWidget(stereo_slider)
    hbox_stereo.addWidget(btn_plus_stereo)

    #close button
    close_button = QPushButton(text=lpak.get("Close", language))
    close_button.clicked.connect(dialog.close)

    #build all
    layout.addWidget(label_stereo_volume)
    layout.addLayout(hbox_stereo)
    layout.addWidget(label_mic_volume)
    layout.addLayout(hbox_mic)
    layout.addWidget(close_button)

    dialog.setLayout(layout)
    dialog.exec()

up_bar_layout = QHBoxLayout()
up_bar_layout.setContentsMargins(10, 10, 10, 10)

microphone_icon = QPushButton(text="🎤")
microphone_icon.setFixedSize(40, 40)
microphone_icon.clicked.connect(ask_ai)

status_label = QLabel(text=f"{lpak.get('Welcome', language)}!")
status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")

menu_button = QPushButton(text="☰") 
menu_button.setFixedSize(40, 40)

button_style = """
    QPushButton {
        background-color: transparent;
        border: none;
        border-radius: 8px;
        font-size: 20px;
    }
    QPushButton:hover {
        background-color: #e0e0e0;
    }
    QPushButton::menu-indicator { 
        image: none; 
    }
"""
microphone_icon.setStyleSheet(button_style)
menu_button.setStyleSheet(button_style)

dropdown_menu = QMenu()
dropdown_menu.setStyleSheet("""
    QMenu {
        background-color: #ffffff;
        border: 1px solid #dcdcdc;
        border-radius: 8px;
        padding: 5px;
    }
    QMenu::item {
        padding: 8px 30px 8px 20px;
        font-size: 15px;
        color: #333;
        border-radius: 5px;
        margin: 2px 0px;
    }
    QMenu::item:selected {
        background-color: #0078D7;
        color: #ffffff;
    }
""")

action_audio = QAction(f"🔊 {lpak.get("Volume", language)}")
action_bluetooth_settings = QAction(f">ᛒ {lpak.get("Bluetooth settings", language)}")
action_settings = QAction(f"⚙️ {lpak.get("Settings", language)}", menu_button) 
action_store = QAction("🏪 Store", menu_button)
action_energy_options = QAction(f"🔋 {lpak.get("Energy options", language)}", menu_button)

action_audio.triggered.connect(show_volume_popup)
action_settings.triggered.connect(open_settings_page)
#action_store.triggered.connect(open_store_page)
action_energy_options.triggered.connect(show_energy_popup)
action_bluetooth_settings.triggered.connect(lambda: open_bluetooth_window())

dropdown_menu.addAction(action_audio)
dropdown_menu.addAction(action_bluetooth_settings)
dropdown_menu.addAction(action_settings)
#dropdown_menu.addAction(action_store)
dropdown_menu.addAction(action_energy_options)

menu_button.setMenu(dropdown_menu)

up_bar_layout.addWidget(microphone_icon, alignment=Qt.AlignmentFlag.AlignLeft)
up_bar_layout.addWidget(status_label, alignment=Qt.AlignmentFlag.AlignLeft)

up_bar_layout.addStretch() 
up_bar_layout.addWidget(menu_button, alignment=Qt.AlignmentFlag.AlignRight)

main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
main_layout.addLayout(up_bar_layout)


#### Central data 
#time
time_string = datetime.datetime.now().strftime("%H:%M \n %d/%m/%Y")
label_time = QLabel(text=time_string)
label_time.setStyleSheet(style_widget)
label_time.setAlignment(Qt.AlignmentFlag.AlignCenter)

#music
music_container, music_artist, music_title, music_title_label, music_album, music_play_button = None, None, None, None, None, None
music_next_song_button, music_previus_song_button, music_volume_up_button, music_volume_down_button, music_layout, music_cover_label = None, None, None, None, None, None

def get_target_player():
    try:
        players = subprocess.check_output(["playerctl", "-l"], text=True).splitlines()
        
        # PRIORITÀ 1: Se esiste un'istanza fake di MPV, 
        # significa che stiamo leggendo un CD. Il comando VA a VLC.
        for p in players:
            if p.startswith("mpv.instance-"):
                return "vlc"

        # PRIORITÀ 2: Se VLC è aperto (anche senza CD), usiamo quello
        if "vlc" in players:
            return "vlc"

        # PRIORITÀ 3: Altrimenti usiamo il player attivo rilevato dall'interfaccia
        if active_player_name:
            return active_player_name

        return None
    except:
        return None

def next_song_command(_checked=False):
    target = get_target_player()
    if target:
        # Usiamo Popen per non bloccare la UI
        subprocess.Popen(["playerctl", "-p", target, "next"])

def previous_song_command(_checked=False):
    target = get_target_player()
    if target:
        subprocess.Popen(["playerctl", "-p", target, "previous"])

def play_song_command(_checked=False):
    target = get_target_player()
    if target:
        subprocess.Popen(["playerctl", "-p", target, "play-pause"])
def turn_up_volume():
    try:
        original_volume = mixer.getvolume()[0]
        volume = original_volume + 5
        mixer.setvolume(volume)
        with open("data/audio_volume.data", "w") as f:
            f.write(str(volume).strip())
    except:
        pass
def turn_down_volume():
    try:
        original_volume = mixer.getvolume()[0]
        volume = original_volume - 5
        mixer.setvolume(volume)
        with open("data/audio_volume.data", "w") as f:
            f.write(str(volume))
    except:
        pass

def create_music_widget():
    global music_container, music_artist, music_title, music_title_label, music_album, music_play_button, music_cover_label
    global music_next_song_button, music_previus_song_button, music_volume_up_button, music_volume_down_button, music_layout
    music_container = QWidget()
    music_container.setStyleSheet(style_widget)
    music_layout = QGridLayout(music_container) 

    music_artist = QLabel()
    music_artist.setStyleSheet("background-color: transparent; border: none;") 
    music_title = QLabel(text=f"{lpak.get("Initialization", language)}...")
    music_title.setStyleSheet("background-color: transparent; border: none;") 
    music_album = QLabel()
    music_album.setStyleSheet("background-color: transparent; border: none;") 

    music_cover_label = QLabel()
    music_cover_label.setFixedSize(120, 120) 
    music_cover_label.setStyleSheet("background-color: #ddd; border-radius: 10px;")
    music_cover_label.setScaledContents(True)

    music_play_button = QPushButton(text="▶️")
    music_play_button.clicked.connect(play_song_command)
    music_next_song_button = QPushButton(text="⏭️")
    music_next_song_button.clicked.connect(next_song_command)
    music_previus_song_button = QPushButton(text="⏮️")
    music_previus_song_button.clicked.connect(previous_song_command)
    music_volume_up_button = QPushButton(text="🔊")
    music_volume_up_button.clicked.connect(turn_up_volume)
    music_volume_down_button = QPushButton(text="🔉")
    music_volume_down_button.clicked.connect(turn_down_volume)

    buttons = [music_previus_song_button, music_play_button, music_next_song_button,music_volume_down_button, music_volume_up_button]
    for btn in buttons:
        btn.setFixedSize(50, 50)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border-radius: 10px;
                font-size: 20px;
                border: 1px solid #c0dfc0;
                
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
    buttons_layout = QHBoxLayout()
    buttons_layout.addWidget(music_volume_down_button)
    buttons_layout.addSpacing(10) 
    buttons_layout.addWidget(music_previus_song_button)
    buttons_layout.addSpacing(10) 
    buttons_layout.addWidget(music_play_button)
    buttons_layout.addSpacing(10)
    buttons_layout.addWidget(music_next_song_button)
    buttons_layout.addSpacing(10) 
    buttons_layout.addWidget(music_volume_up_button)

    music_layout.addWidget(music_artist, 0, 1)
    music_layout.addWidget(music_title, 1, 1)
    music_layout.addWidget(music_album, 2, 1)
    music_layout.addWidget(music_cover_label, 0, 0, 3, 1)
    music_layout.addLayout(buttons_layout, 3, 0, 1, 2)

if setting_status(music_widget_status):
    music_play_button = None
    create_music_widget()

#calendar
calendar_container, calendar_layout, title_event_label = None, None, None
def create_calendar_widget():
    global calendar_container, calendar_layout, title_event_label
    calendar_container = QWidget()
    calendar_container.setStyleSheet(style_widget)
    calendar_layout = QGridLayout()
    title_event_label = QLabel(text=lpak.get("Calendar", language).upper())
    title_event_label.setStyleSheet("font: bold")
    calendar_layout.addWidget(title_event_label, 0, 0, 1, 2)
    calendar_container.setLayout(calendar_layout)
if setting_status(calendar_widget_status):
    create_calendar_widget()

#Wheater
weather_container, weather_layout = None, None

def create_weather_widget():    
    global weather_container, weather_layout

    def get_weather_text(weather):
        weather_translation=lpak.get(weather, language)
        if weather == "Clear sky":
            emoji = "☀️"
        elif weather == "Mainly clear":
            emoji = "🌤️"
        elif weather == "Partly cloudy":
            emoji = "⛅"
        elif weather == "Overcast":
            emoji = "☁️"
        elif weather == "Fog":
            emoji = "🌫️"
        elif weather == "Freezing fog":
            emoji = "❄️🌫️"
        elif weather == "Light drizzle":
            emoji = "🌦️"
        elif weather == "Moderate drizzle":
            emoji = "🌧️"
        elif weather == "Dense drizzle":
            emoji = "🌧️"
        elif weather == "Light rain":
            emoji = "🌦️"
        elif weather == "Moderate rain":
            emoji = "🌧️"
        elif weather == "Heavy rain":
            emoji = "🌧️"
        elif weather == "Light snow":
            emoji = "🌨️"
        elif weather == "Moderate snow":
            emoji = "❄️"
        elif weather == "Heavy snow":
            emoji = "☃️"
        elif weather == "Light rain showers":
            emoji = "🌦️"
        elif weather == "Moderate rain showers":
            emoji = "🌧️"
        elif weather == "Violent rain showers":
            emoji = "⛈️"
        elif weather == "Thunderstorm":
            emoji = "⚡"
        else:
            emoji = "❓"
        return f"{weather_translation} - {emoji}"
    
    h=time_now = datetime.datetime.now().strftime("%H")   
    weather_data = get_weather(city, 0, int(h)+1)
    temperature=weather_data["temperature"]
    apparent_temperature=weather_data["apparent_temperature"]
    weather=weather_data["weather"]
    weather = get_weather_text(weather)

    
    weather_container = QWidget()
    weather_container.setStyleSheet(style_widget)

    
    weather_layout = QGridLayout(weather_container)

    weather_label = QLabel(weather)
    weather_label.setStyleSheet("""
        font-size: 30pt; 
        font-weight: bold; 
        font-style: italic;
    """)
    weather_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    temperaute_label = QLabel(f"{lpak.get("Temperature", language)}: {temperature} - {lpak.get("Feels-like temperature", language)}: {apparent_temperature}")
    temperaute_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    weather_layout.addWidget(weather_label, 0, 0)
    weather_layout.addWidget(temperaute_label, 1, 0)

if setting_status(weather_widget_status):
    create_weather_widget()

def create_images_widget():
    global images_container, images_layout, image_label

    images_container = QWidget()
    images_container.setStyleSheet(style_widget)

    images_layout = QGridLayout()

    image_label = QLabel(f"{lpak.get("Loading", language)}...")
    
    image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    image_label.setMinimumSize(300, 200)

    image_label.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding
    )

    image_label._opacity = QGraphicsOpacityEffect()
    image_label.setGraphicsEffect(image_label._opacity)
    image_label._opacity.setOpacity(1.0)

    images_layout.addWidget(image_label)

    images_container.setLayout(images_layout)

images_widget_status = "Enable"
if setting_status(images_widget_status):
   create_images_widget()

#Make Layout
def control_coordinate():   
    global line, column
    if column == 1:
        column = 0
        line = line+1
    else:
        column = 1

line = 0
column = 0
#Layout tot
data_widget = QGridLayout()
data_widget.addWidget(label_time, line, column) 
control_coordinate()
if setting_status(music_widget_status):
    data_widget.addWidget(music_container, line, column) 
    control_coordinate()
if setting_status(calendar_widget_status):
    data_widget.addWidget(calendar_container, line, column)
    control_coordinate()
if setting_status(weather_widget_status):
    data_widget.addWidget(weather_container, line, column)
    control_coordinate()
if setting_status(images_widget_status):
    data_widget.addWidget(images_container, line, column)
    control_coordinate()


def load_external_widgets(griglia_layout, starting_line=1, starting_column=1):
    ui_path = "apps/UI"
    print("1. Starting plugin loading...")    

    if not os.path.exists(ui_path):
        print(f"Directory {ui_path} not found!")
        return

    current_line = starting_line
    current_column = starting_column

    for folder_name in os.listdir(ui_path):
        plugin_path = os.path.join(ui_path, folder_name)
        print(f"2. Folder found: {folder_name}")        

        if not (os.path.isdir(plugin_path) and os.path.exists(os.path.join(plugin_path, "manifest.json"))):
            continue

        try:
            status_file = os.path.join(plugin_path, "status.conf")

            if not os.path.isfile(status_file):
                with open(status_file, "w") as f:
                    f.write("disable")

            with open(status_file, "r") as f:
                status = f.readline().strip().lower()

            if status != "enable":
                print(f"{folder_name} disabled")
                continue

            print(f"3. Reading manifest {folder_name}")
            with open(os.path.join(plugin_path, "manifest.json"), "r") as f:
                manifest = json.load(f)

            if not manifest.get("attivo", True):
                continue

            file_python_name = manifest['main'].replace(".py", "")
            class_name = manifest['main_class']
            module_name = f"apps.UI.{folder_name}.{file_python_name}"

            print(f"4. Importing: {module_name}")
            loaded_module = importlib.import_module(module_name)

            ClasseWidget = getattr(loaded_module, class_name)
            plugin_instance = ClasseWidget()

            print("6. Enabling widget")
            plugin_instance.on_enable()
            widget_ui = plugin_instance.get_widget()

            griglia_layout.addWidget(widget_ui, current_line, current_column)
            print(f"7. Widget {folder_name} loaded!")

            current_column += 1
            if current_column > 1:
                current_column = 0
                current_line += 1

        except Exception as e:
            print(f"FATAL ERROR in widget: {folder_name}: {e}")
            import traceback
            traceback.print_exc()

    print("8. Widget loaded!")

load_external_widgets(data_widget, starting_line=line, starting_column=column)


data_widget.setColumnStretch(0, 1)
data_widget.setColumnStretch(1, 1)


main_layout.addLayout(data_widget)

# TIMER update
rapid_update_timer = QTimer()
rapid_update_timer.timeout.connect(update_gui)
rapid_update_timer.start(1500)

long_update_timer = QTimer()
long_update_timer.timeout.connect(long_update_widget)
long_update_timer.start(300000)

#Photos timer
images_timer = QTimer()
images_timer.timeout.connect(update_imagesFrame)
images_timer.start(7000)

first_load()
wait_keyword()


if test_mode_enable():
    root.showMaximized()
else:
    root.showFullScreen()
splash.finish(root)
sys.exit(app.exec())