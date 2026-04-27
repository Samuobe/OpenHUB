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

music_widget_status = config.get("Widgets", "Music")
calendar_widget_status = config.get("Widgets", "Calendar")

def setting_status(a):
    if a=="Enable":
        return True
    else:
        return False



musicbrainzngs.set_useragent("OpenHUB", "0.1", "https://github.com/Samuobe/OpenHUB")

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

#global gabbage

last_title = ""
active_threads = []


if os.path.isfile(f"{data_path}conversation.json"):
    os.remove(f"{data_path}conversation.json")



def show_big_advice(testo):
    global current_popup
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
    wait_keyword()

def clear_layout(layout, keep=1):
    while layout.count() > keep:
        item = layout.takeAt(keep)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()

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
        self.artist = artist
        self.album = album
        self.title = title

    def run(self):
        try:
            search_query = self.album if self.album and len(self.album) > 2 else self.title
            result = musicbrainzngs.search_releases(artist=self.artist, release=search_query, limit=1)
            
            if result['release-list']:
                release_id = result['release-list'][0]['id']
                url = f"https://coverartarchive.org/release/{release_id}/front-250"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    self.finished.emit(response.content) 
                    return
            
            self.finished.emit(None)
        except Exception as e:
            print(f"Cover error: {e}")
            self.finished.emit(None)

class VoiceWorker(QThread):
    finished = pyqtSignal(str)
    def run(self):
        try:
            prompt = voice_input(turn_down_volume=True)
            self.finished.emit(prompt if prompt else "")
        except:
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
    
def update_music():
    global last_title, current_cover_thread
    global music_container, music_artist, music_title, music_title_label, music_album, music_play_button, music_cover_label
    global music_next_song_button, music_previus_song_button, music_volume_up_button, music_volume_down_button, music_layout
    
    def set_cover_or_emoji(result):
        if result:
            pixmap = QPixmap()
            pixmap.loadFromData(result)
            music_cover_label.setPixmap(pixmap)
            music_cover_label.setText("") 
        else:
            music_cover_label.setPixmap(QPixmap()) 
            music_cover_label.setText("🎵")
            music_cover_label.setStyleSheet("""
                background-color: #ddd; 
                border-radius: 10px; 
                font-size: 70px; 
                text-align: center;
            """)
            music_cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    try:
        if is_mpv_running():
            music_data_raw = subprocess.check_output(
                ["playerctl", "-p", "mpv","metadata", "--format", "{{xesam:artist}}|||{{xesam:title}}|||{{xesam:album}}|||{{position}}|||{{status}}|||{{volume}}|||{{duration}}|||{{playerName}}"],
                timeout=0.2,
                text=True,
                stderr=subprocess.DEVNULL
            )
        else:
            music_data_raw = subprocess.check_output(
                ["playerctl", "metadata", "--format", "{{xesam:artist}}|||{{xesam:title}}|||{{xesam:album}}|||{{position}}|||{{status}}|||{{volume}}|||{{duration}}|||{{playerName}}"],
                timeout=0.2,
                text=True,
                stderr=subprocess.DEVNULL
            )
        music_data = music_data_raw.strip().split("|||")
        
        if len(music_data) >= 5:
            artist = music_data[0]
            title = music_data[1]
            album = music_data[2]
            music_status = music_data[4]
        
            if title != last_title:
                last_title = title
                music_artist.setText(f"{lpak.get("Artist", language)}: {artist}")
                if "stream.view?" in title:
                    music_title.setText(f"{lpak.get("Loading", language)}...")
                else:
                    music_title.setText(f"{lpak.get("Title", language)}: {title}")
                music_album.setText(f"{lpak.get("Album", language)}: {album}")

                music_cover_label.setPixmap(QPixmap())
                music_cover_label.setText("⏳")
                music_cover_label.setStyleSheet("""
                        background-color: #ddd; 
                        border-radius: 10px; 
                        font-size: 70px; 
                        text-align: center;
                    """) 

         
                new_cover_thread = CoverWorker(artist, album, title)
                active_threads.append(new_cover_thread)

                def cleanup_and_set(result, thread_ref=new_cover_thread):
                    set_cover_or_emoji(result)
                    if thread_ref in active_threads:
                        active_threads.remove(thread_ref)
                        
                new_cover_thread.finished.connect(cleanup_and_set)
                new_cover_thread.start()
                
            if music_status == "Playing":
                music_play_button.setText("⏸️")
                music_play_button.clicked.connect(lambda: play_song_command(2))
            else:
                music_play_button.setText("▶️")
                music_play_button.clicked.connect(lambda: play_song_command(1))
                
    except subprocess.TimeoutExpired:
        pass

    except subprocess.CalledProcessError:
        title = lpak.get("Nothing is playing", language)
        music_title.setText(title)
        music_artist.setText("")
        music_album.setText("")
        music_cover_label.setPixmap(QPixmap())
        music_cover_label.setText("🎵")
        last_title = ""

def update_gui():
    update_time()
    if setting_status(music_widget_status):
        update_music()
    root.repaint()


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
    if setting_status(calendar_widget_status):
        load_calendar()

def load_static_data():
    print("No static data for now!")

def first_load():
    load_static_data()
    load_calendar()


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
#END SPALSH


#LIBRERIE
from PyQt6.QtWidgets import QMainWindow, QHBoxLayout, QPushButton, QVBoxLayout, QWidget, QLabel, QDialog, QGridLayout
import datetime
from PyQt6.QtCore import QTime, Qt, QTimer
from PyQt6.QtWidgets import QLabel, QPushButton, QScrollArea, QFrame, QMenu
import re
import requests
from Lattuga.lattuga import voice_input, Lattuga, manual_input
from Lattuga.tools import get_events
from other_windows.app_store import open_store_page
import subprocess
from functions.mpv_status import is_mpv_running
import alsaaudio
import importlib
import json
from other_windows.settings import open_settings_page
from PyQt6.QtGui import QAction
from other_windows.bluetooth_manager import open_bluetooth_window
import Lattuga.tools as my_tools



mixer = alsaaudio.Mixer()

config.read("credential.env")
device_name = config.get("Device info", "device_name")




root = QMainWindow()
root.setWindowTitle("OpenHUB")


central_widget = QWidget()
root.setCentralWidget(central_widget)
main_layout = QVBoxLayout(central_widget)


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
    btn_shutdown.setObjectName("shutdown")
    btn_restart = QPushButton(lpak.get("System reboot", language))
    btn_restart.setObjectName("shutdown")
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

action_bluetooth_settings = QAction(f">ᛒ {lpak.get("Bluetooth settings", language)}")
action_settings = QAction(f"⚙️ {lpak.get("Settings", language)}", menu_button) 
action_store = QAction("🏪 Store", menu_button)
action_energy_options = QAction(f"🔋 {lpak.get("Energy options", language)}", menu_button)

action_settings.triggered.connect(open_settings_page)
#action_store.triggered.connect(open_store_page)
action_energy_options.triggered.connect(show_energy_popup)
action_bluetooth_settings.triggered.connect(lambda: open_bluetooth_window())

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
def next_song_command():
    if is_mpv_running():
        os.system('playerctl -p "mpv" next')
    else: 
        os.system("playerctl next")
def previous_song_command():
    if is_mpv_running():
        os.system('playerctl -p "mpv" previous')
    else: 
        os.system("playerctl previous")
def play_song_command(action):
    if action==1:
        if is_mpv_running():
            os.system('playerctl -p "mpv" play')
        else: 
            os.system("playerctl play")
    else:
        if is_mpv_running():
            os.system('playerctl -p "mpv" pause')
        else: 
            os.system("playerctl pause")
def turn_up_volume():
    try:
        original_volume = mixer.getvolume()[0]
        mixer.setvolume(original_volume+ 5)
    except:
        pass
def turn_down_volume():
    try:
        original_volume = mixer.getvolume()[0]
        mixer.setvolume(original_volume- 5)
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
create_calendar_widget()

#Wheater



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




main_layout.addLayout(data_widget)
# TIMER update
rapid_update_timer = QTimer()
rapid_update_timer.timeout.connect(update_gui)
rapid_update_timer.start(500)

long_update_timer = QTimer()
long_update_timer.timeout.connect(long_update_widget)
long_update_timer.start(300)

first_load()
wait_keyword()


if test_mode_enable():
    root.showMaximized()
else:
    root.showFullScreen()
splash.finish(root)
sys.exit(app.exec())