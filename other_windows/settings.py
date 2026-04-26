import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QGridLayout, QFrame, QProgressBar, QMessageBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import configparser
import glob
import functions.lpak as lpak
import json
import functions.notify as notify
import config_process
import shutil


settings_window = None 
config = None
setting_status_label = None
update_thread = None

NO_OVERWRITE_FILES = ["config.conf","credential.env", "instalation_type.info" ]

class UpdateThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str) 

    def __init__(self, install_type, parent=None):
        super().__init__(parent)
        self.install_type = install_type

    def run(self):
        import subprocess
        import os, shutil, tempfile, json

        if self.install_type == "main":
            try:
                self.progress.emit(10)
                subprocess.check_call(['git', 'pull'], cwd=os.getcwd())
                ver = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=os.getcwd()).decode().strip()
            except Exception as e:
                self.finished.emit(f"Errore aggiornamento: {e}")
                return
            self.progress.emit(100)
            self.finished.emit(f"main ({ver})")
        elif self.install_type == "stable":
            self.progress.emit(5)
            try:
                import requests
                r = requests.get('https://api.github.com/repos/Samuobe/OpenHUB/releases/latest')
                d = r.json()
                zip_url = d.get("zipball_url")
                relver = d.get("tag_name")

                if not zip_url or not relver:
                    self.finished.emit("Source ZIP release non trovata!")
                    return

                self.progress.emit(20)
                tmpdir = tempfile.mkdtemp()
                zippath = os.path.join(tmpdir, 'release.zip')
                with requests.get(zip_url, stream=True) as resp, open(zippath, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                self.progress.emit(40)

                import zipfile
                with zipfile.ZipFile(zippath, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                folder = [f for f in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, f))][0]
                srcdir = os.path.join(tmpdir, folder)
                dstdir = os.getcwd()
                for root, dirs, files in os.walk(srcdir):
                    rel_root = os.path.relpath(root, srcdir)
                    for file in files:
                        rel_path = os.path.normpath(os.path.join(rel_root, file))
                        if rel_path in NO_OVERWRITE_FILES:
                            continue
                        src = os.path.join(root, file)
                        dst = os.path.join(dstdir, rel_path)
                        dst_folder = os.path.dirname(dst)
                        if not os.path.exists(dst_folder):
                            os.makedirs(dst_folder, exist_ok=True)
                        shutil.copy2(src, dst)
                self.progress.emit(90)
                shutil.rmtree(tmpdir)
                self.progress.emit(100)
                self.finished.emit(f"stable ({relver})")
            except Exception as e:
                self.finished.emit(f"Errore aggiornamento: {e}")
                return

def open_settings_page():
    shutil.copyfile("config.conf","config.conf.old")
    shutil.copyfile("credential.env","credential.env.old")
    def test_mode_enable():    
        return os.path.isfile("test.txt")
    data_path = ""
    global settings_window, config, setting_status_label
    global language, music_widget_status, calendar_widget_status

    avaible_languages_temp = glob.glob(f"{data_path}lpak/*.lpak")
    avaible_languages = []
    for language in avaible_languages_temp:
        avaible_languages.append(language.split("/")[-1].split(".")[0])
    avaible_languages.sort(key=str.lower)

    def set_edited_status():
        global setting_status_label
        setting_status_label.setText(lpak.get("Close to confirm changes", language))

    def setting_status(a):
        if a.strip().lower()=="enable":
            return True
        else:
            return False

    config =configparser.ConfigParser()
    config.optionxform = str
    config.read(f"{data_path}config.conf")
    language = config.get("User data", "Language")

    music_widget_status = config.get("Widgets", "Music")
    calendar_widget_status = config.get("Widgets", "Calendar")

    with open("info/instalation_type.info", "r") as f:
        instalation_type = f.readlines()[0]
        if instalation_type == "main":
            instalation_type_user = lpak.get("main", language)
        elif instalation_type == "stable":
            instalation_type_user = lpak.get("stable",language)

    def get_openhub_version():
        try:
            version = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                stderr=subprocess.STDOUT
            ).decode().strip()
            if version:
                return version
        except Exception:
            pass
        try:
            with open(os.path.join("info", "ver.info"), "r") as f:
                version = f.readline().strip()
                if version:
                    return version
        except Exception:
            pass
        return "(versione sconosciuta)"


    def write_settings():
        global config
        with open(f"{data_path}config.conf", "w") as configfile:
                config.write(configfile)

    def close_window():
        global config
        with open(f"{data_path}config.conf", "w") as configfile:
            config.write(configfile)
        try:
            with open('config.conf', 'r') as f1:
                new_config = f1.read()

            with open('config.conf.old', 'r') as f2:
                old_config = f2.read()
            os.remove("config.conf.old")

            with open('credential.env', 'r') as f1:
                new_credential = f1.read()

            with open('credential.env.old', 'r') as f2:
                old_credentuial = f2.read()
            os.remove("credential.env.old")

            if new_config != old_config or new_credential != old_credentuial:
                os.system("systemctl --user restart openhub.service")  
            else:
                pass 

        except Exception as e:
            print("Error during confronting:", e)
    
        settings_window.close()        

    if settings_window is not None:
        settings_window.show()  
        settings_window.raise_()
        return settings_window

    settings_window = QMainWindow()
    settings_window.setWindowTitle(f"OpenHUB - {lpak.get('Settings', language)}")

    central_widget = QWidget()
    settings_window.setCentralWidget(central_widget)
    main_layout = QVBoxLayout(central_widget)

    # Up bar
    up_bar_layout = QHBoxLayout()
    status_label = QLabel(f"{lpak.get('Settings', language)}")
    close_button = QPushButton("❌")

    close_button.clicked.connect(close_window)

    up_bar_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignLeft)
    up_bar_layout.addWidget(status_label)
   
    up_bar_layout.addStretch()

    main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    main_layout.setContentsMargins(10, 10, 10, 10)
    main_layout.addLayout(up_bar_layout)

    def create_line():
        l = QFrame()
        l.setFrameShape(QFrame.Shape.HLine)
        l.setFrameShadow(QFrame.Shadow.Sunken)
        return l

    main_layout.addWidget(create_line())

    # central content
    label_title = QLabel(f"{lpak.get('Settings', language)}")
    label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

    label_user_data=QLabel(f"{lpak.get('Interface options', language)}")
    #languages
    label_language=QLabel(lpak.get("Language", language))
    menu_select_language = QComboBox()
    menu_select_language.addItems(avaible_languages)
    menu_select_language.setCurrentText(language)

    #Widgets
    label_widget_title = QLabel(lpak.get("Default widgets", language))
    def change_music_widget_status():
        global music_widget_status, config
        set_edited_status()
        if setting_status(music_widget_status):
            val = "Disable"
            button_setting_music.setText(lpak.get("Enable", language))
        else:
            val = "Enable"
            button_setting_music.setText(lpak.get("Disable", language))
        music_widget_status = val
        config.set("Widgets", "Music", val)
        write_settings()

    label_music_widget = QLabel("Musica")
    button_setting_music =QPushButton()
    button_setting_music.clicked.connect(change_music_widget_status)
    if setting_status(music_widget_status):
        button_setting_music.setText(lpak.get("Disable", language))
    else:
        button_setting_music.setText(lpak.get("Enable", language))  
    
    def change_calendar_widget_status():
        global calendar_widget_status, config
        set_edited_status()
        if setting_status(calendar_widget_status):
            val = "Disable"
            button_setting_calendar.setText(lpak.get("Enable", language))
        else:
            val = "Enable"
            button_setting_calendar.setText(lpak.get("Disable", language))
        calendar_widget_status = val
        config.set("Widgets", "Calendar", val)
        write_settings()

    label_calendar_widget = QLabel(lpak.get("Calendar", language))
    button_setting_calendar = QPushButton()
    button_setting_calendar.clicked.connect(change_calendar_widget_status)

    if setting_status(calendar_widget_status):
        button_setting_calendar.setText(lpak.get("Disable", language))
    else:
        button_setting_calendar.setText(lpak.get("Enable", language))

    #label
    setting_status_label = QLabel()

    #Buttons
    def change_language():
        global config
        set_edited_status()
        new_language = menu_select_language.currentText()
        config.set("User data", "Language", new_language)
        write_settings()
        notify.system_notification(f"{lpak.get('New language', new_language)}: {new_language}", f"{lpak.get('Language updated', new_language)}. {lpak.get('Language updated', new_language)}!")

    button_change_language = QPushButton(lpak.get("Apply language", language))
    button_change_language.clicked.connect(change_language)

    #reconfig button
    def start_reconfig():
        config_process.restart_configuration(use_gui=True)
    button_edit_credential = QPushButton(lpak.get("Edit services credentials", language)) 
    button_edit_credential.clicked.connect(start_reconfig)

    data_widget = QGridLayout()
    data_widget.setHorizontalSpacing(20) 
    
    data_widget.addWidget(label_title, 0, 0, 1, 4)

    data_widget.addWidget(label_user_data, 1, 0, 1, 2)
    data_widget.addWidget(label_language, 2, 0, 1, 1)
    data_widget.addWidget(menu_select_language, 2, 1, 1, 1)
    data_widget.addWidget(create_line(), 3, 0, 1, 2)

    data_widget.addWidget(label_widget_title, 4, 0, 1, 2)
    data_widget.addWidget(label_music_widget, 5, 0, 1, 1)
    data_widget.addWidget(button_setting_music, 5, 1, 1, 1)    
    data_widget.addWidget(label_calendar_widget, 6, 0, 1, 1)
    data_widget.addWidget(button_setting_calendar, 6, 1, 1, 1)
    
    data_widget.addWidget(create_line(), 7, 0, 1, 2)
    data_widget.addWidget(button_change_language, 8, 0, 1, 2)


    label_title_custom_things=QLabel("Custom component")
    label_title_custom_widgets=QLabel("Custom label")

    def change_custom_widget_status(path, status, button):
        if button.text() == lpak.get("Disable", language):
            with open(path+"/status.conf", "w") as f:
                f.write("disable")
                button.setText(lpak.get("Enable", language))
        else:
            with open(path+"/status.conf", "w") as f:
                f.write("enable")
                button.setText(lpak.get("Disable", language))

    avaible_custom_widgets = []
    custom_widgets_path = f"{data_path}apps/UI"
    
    if os.path.exists(custom_widgets_path):
        for folder in os.listdir(custom_widgets_path):
            folder_path = os.path.join(custom_widgets_path, folder)
            if os.path.isdir(folder_path):
                avaible_custom_widgets.append(folder)
        avaible_custom_widgets.sort(key=str.lower)

    data_widget.addWidget(label_title_custom_things, 1, 2, 1, 2)
    data_widget.addWidget(label_title_custom_widgets, 2, 2, 1, 2)
    
    r = 3
    for plugin in avaible_custom_widgets:
        if plugin == "__init.py__" or plugin == "__pycache__":
            continue
        try:
            with open(f"{custom_widgets_path}/{plugin}/manifest.json", "r") as f:
                data = json.load(f)
            name = data["name"]
        except Exception:
            continue

        plugin_label=QLabel(name)
        plugin_button = QPushButton()
        
        if not os.path.isfile(f"{custom_widgets_path}/{plugin}/status.conf"):
            with open(f"{custom_widgets_path}/{plugin}/status.conf", "w") as f:
                f.write("disable")
        with open(f"{custom_widgets_path}/{plugin}/status.conf", "r") as f:
            status = f.readline().strip().lower()
            
        plugin_button.clicked.connect(lambda checked=False, p=plugin, s=status, b=plugin_button: change_custom_widget_status(custom_widgets_path+"/"+p, s, b))
        
        if setting_status(status):
            plugin_button.setText(lpak.get("Disable", language))
        else:
            plugin_button.setText(lpak.get("Enable", language))

        data_widget.addWidget(plugin_label, r, 2, 1, 1)
        data_widget.addWidget(plugin_button, r, 3, 1, 1)
        r = r+1

    bottom_row = max(9, r)

    data_widget.addWidget(create_line(), bottom_row, 0, 1, 4)
    data_widget.addWidget(button_edit_credential, bottom_row + 1, 0, 1, 4)
    data_widget.addWidget(setting_status_label, bottom_row+2,0,1, 1)

    update_progress = QProgressBar()
    update_progress.setVisible(False)

    update_status_label = QLabel()
    update_status_label.setVisible(False)

    restart_button = QPushButton("Riavvia OpenHUB")
    restart_button.setVisible(False)

    def on_restart():
        os.system("systemctl --user restart openhub.service")
        pass
    restart_button.clicked.connect(on_restart)

    def start_update():
        global update_thread
        update_progress.setVisible(True)
        update_progress.setValue(0)
        update_status_label.setVisible(True)
        update_status_label.setText("Aggiornamento in corso, attendere...")

        restart_button.setVisible(False)
        _inst_type = instalation_type.strip()
        update_thread = UpdateThread(_inst_type)
        update_thread.progress.connect(update_progress.setValue)

        def on_update_finished(msg):
            update_status_label.setText(f"Aggiornamento terminato: {msg}")
            update_progress.setVisible(False)
            restart_button.setVisible(True)
            global update_thread
            update_thread = None

        update_thread.finished.connect(on_update_finished)
        update_thread.start()

    start_update_button = QPushButton(text="Aggiorna")
    start_update_button.clicked.connect(start_update)
    #version_label=QLabel(f"{instalation_type_user} - {get_openhub_version()}")



    r = bottom_row+3 
    data_widget.addWidget(start_update_button, r,0,1,1)
    data_widget.addWidget(version_label, r+1,0,1,1)
    data_widget.addWidget(update_progress, r,1,1,2)
    data_widget.addWidget(update_status_label, r+1,0,1,3)
    data_widget.addWidget(restart_button, r+2,0,1,3)


    data_widget.setColumnStretch(0, 1)
    data_widget.setColumnStretch(1, 1)
    data_widget.setColumnStretch(2, 1)
    data_widget.setColumnStretch(3, 1)

    main_layout.addLayout(data_widget)
    main_layout.addStretch()

    if test_mode_enable():
        settings_window.showMaximized()
    else:
        settings_window.showFullScreen()
    return settings_window

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    open_settings_page()
    sys.exit(app.exec())