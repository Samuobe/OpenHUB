import sys
import os
import configparser
import socket
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
import functions.lpak as lpak

def test_mode_enable():    
    return os.path.isfile("test.txt")

config =configparser.ConfigParser()
config.read("config.conf")
language = config.get("User data", "Language")


config_file = "credential.env"
config = configparser.ConfigParser()
config.optionxform = str 

app_state = {
    "sections_to_configure": []
}

CONFIG_SCHEMA = [
    {
        "name": "Device info",
        "keys": ["device_name"],
        "optional": False
    },
    {
        "name": "CALDAV",
        "keys": ["caldav_url", "caldav_username", "caldav_password"],
        "optional": True
    },
    {
        "name": "Home Assistant",
        "keys": ["home_assistant_url", "home_assistant_token"],
        "optional": True
    },
    {
        "name": "Subsonic",
        "keys": ["SUBSONIC_URL", "SUBSONIC_USERNAME", "SUBSONIC_PASSWORD"],
        "optional": True
    }
]

# ==========================================
# WEB SERVER
# ==========================================
WEB_PORT = 8080

class WebServerSignals(QObject):
    finished = pyqtSignal()

web_signals = WebServerSignals()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

class SetupHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            html = """
            <html>
            <head>
                <title>"""+lpak.get("Setup OpenHomeHUB", language)+"""</title>
                <style>
                    body { font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px; }
                    .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                    h2 { color: #333; border-bottom: 2px solid #0078D7; padding-bottom: 5px; }
                    label { font-weight: bold; display: block; margin-top: 10px; }
                    input[type="text"], input[type="password"] { width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
                    .btn { display: block; width: 100%; background: #28A745; color: white; padding: 10px; border: none; border-radius: 5px; font-size: 16px; margin-top: 20px; cursor: pointer; }
                    .btn:hover { background: #218838; }
                    .optional { color: #888; font-size: 12px; font-weight: normal; }
                    .guide-box { background-color: #e7f3fe; border-left: 4px solid #0078D7; padding: 10px; margin-bottom: 15px; font-size: 14px; color: #333; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 style="text-align: center; color: #0078D7;">"""+lpak.get("Setup OpenHomeHUB", language)+"""</h1>
                    <form method="POST" action="/save">
            """
            
            for section in app_state["sections_to_configure"]:
                sec_name = section["name"]
                is_optional = section["optional"]
                
                opt_text = f" ({lpak.get("Optional leave blank to skip", language)})" if is_optional else f" ({lpak.get("Required", language)})"
                html += f"<h2>{sec_name}<span class='optional'>{opt_text}</span></h2>"
                
                if sec_name == "Home Assistant":
                    html += f"""
                    <div class="guide-box">
                        <b>{lpak.get("Home Assistant Token Guide", language)}:</b><br>
                        1. {lpak.get("Open your Home Assistant in your browser", language)}.<br>
                        2. {lpak.get("Click on your", language)} <b>{lpak.get("Profile", language)}</b> ({lpak.get("bottom left", language).lower()}).<br>
                        3. {lpak.get("Go to the page", language)} <b>{lpak.get("Security", language)}</b> ({lpak.get("at the top", language)}).<br>
                        4. {lpak.get("Scroll to the bottom of the section", language)} <b>{lpak.get("Long-term tokens", language)}</b>. {lpak.get("Than click", language)} <i>{lpak.get("Create token", language)}</i>.<br>
                        5. {lpak.get("Copy the very long token and paste it below!", language)}
                    </div>
                    """
                
                for key in section["keys"]:
                    input_type = "password" if "password" in key.lower() else "text"
                    req_attr = "" if is_optional else "required"
                    
                    html += f"<label>{key}</label>"
                    html += f"<input type='{input_type}' name='{sec_name}|{key}' {req_attr}>"
            
            html += f"""
                        <button type="submit" class="btn">{lpak.get("Save configuration", language)}</button>
                    </form>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path == "/success":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html = f"""
            <html><body style="font-family: Arial; text-align: center; margin-top: 50px;">
                <h1 style="color: #28A745;">{lpak.get("Configuration saved!", language)}</h1>
                <p>{lpak.get("All data has been saved", language)}.</p>
                <p>{lpak.get("You can close this page, the device is booting up.", language)}</p>
            </body></html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/save":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = urllib.parse.parse_qs(post_data)
            
            if os.path.isfile(config_file):
                config.read(config_file)
            
            for section in app_state["sections_to_configure"]:
                sec_name = section["name"]
                if not config.has_section(sec_name):
                    config.add_section(sec_name)
                
                for key in section["keys"]:
                    form_key = f"{sec_name}|{key}"
                    val = parsed_data.get(form_key, [""])[0].strip()
                    
                    if val == "" and section["optional"]:
                        val = "-"
                        
                    config.set(sec_name, key, val)

            with open(config_file, 'w') as f:
                config.write(f)
                
            self.send_response(303)
            self.send_header("Location", "/success")
            self.end_headers()
            
            web_signals.finished.emit()

def start_web_server():
    server = HTTPServer(('0.0.0.0', WEB_PORT), SetupHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def prepare_config_state():
    if os.path.isfile(config_file):  
        config.read(config_file)
        
    app_state["sections_to_configure"] = []
    
    for section in CONFIG_SCHEMA:
        sec_name = section["name"]
        needs_config = False
        
        if not config.has_section(sec_name):
            needs_config = True
        else:
            for key in section["keys"]:
                if not config.has_option(sec_name, key):
                    needs_config = True
                    break
                
                val = config.get(sec_name, key).strip()
                if val == "":  
                    needs_config = True
                    break
                    
        if needs_config:
            app_state["sections_to_configure"].append(section)


def clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                child_layout = item.layout()
                if child_layout is not None:
                    clear_layout(child_layout)

def show_web_server_info():
    setting_label.setText("Setup via Web")
    clear_layout(central_layout)

    ip_address = get_local_ip()
    
    msg = QLabel(f"{lpak.get("To fill in the missing fields, log in via your browser", language)}:")
    msg.setStyleSheet("font: 14pt; margin-bottom: 10px;")
    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    url_msg = QLabel(f"http://{ip_address}:{WEB_PORT}")
    url_msg.setStyleSheet("font: bold 24pt; color: #0078D7; margin-bottom: 20px;")
    url_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    wait_msg = QLabel(f"{lpak.get("Pending completion from the webpage", language)}...")
    wait_msg.setStyleSheet("font: italic 12pt; color: #666;")
    wait_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

    central_layout.addWidget(msg, alignment=Qt.AlignmentFlag.AlignCenter)
    central_layout.addWidget(url_msg, alignment=Qt.AlignmentFlag.AlignCenter)
    central_layout.addWidget(wait_msg, alignment=Qt.AlignmentFlag.AlignCenter)

def show_finished_screen():
    setting_label.setText(lpak.get("Completed", language))
    clear_layout(central_layout)

    msg = QLabel(f"{lpak.get("Configuration completed successfully", language)}!\n{lpak.get("All data has been saved", language)}.")
    msg.setStyleSheet("font: bold 16pt; margin-bottom: 20px; color: #28A745;")
    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    close_btn = QPushButton(lpak.get("Close and continue", language))
    close_btn.setStyleSheet("""
        QPushButton { background-color: #0078D7; color: white; font: bold 14pt; border-radius: 5px; padding: 10px 20px; }
        QPushButton:hover { background-color: #005A9E; }
    """)
    close_btn.setFixedWidth(200)
    close_btn.pressed.connect(root.close) 

    central_layout.addWidget(msg, alignment=Qt.AlignmentFlag.AlignCenter)
    central_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

def run_setup(use_gui=True):
    global root, central_layout, setting_label
    
    prepare_config_state()
    
    if len(app_state["sections_to_configure"]) == 0:
        print("Everithing is already configured")
        return

    web_server = start_web_server()

    if not use_gui:
        print("\n" + "="*50)
        print("🛠️  CLi setup starting")
        print(f"👉 go to: http://{get_local_ip()}:{WEB_PORT}")
        print("Waiting for configuration...")
        print("="*50 + "\n")
        
        event = threading.Event()
        web_signals.finished.connect(event.set)
        event.wait()
        web_server.shutdown()
        print("✅ Configuration saved, starting system...")
        return

    app = QApplication(sys.argv)
    root = QMainWindow()
    root.setWindowTitle("OpenHomeHUB - CONFIG")

    central_widget = QWidget()
    root.setCentralWidget(central_widget)
    main_layout = QVBoxLayout(central_widget)
    main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    main_layout.setContentsMargins(20, 20, 20, 20)

    up_bar_layout = QHBoxLayout()
    up_bar_style = "font: bold; font-size: 12pt; color: #333;"

    title_label = QLabel(text=f"{lpak.get("Welcome", language)}")
    setting_label = QLabel(text=f"{lpak.get("Home", language)}")
    title_label.setStyleSheet(up_bar_style)
    setting_label.setStyleSheet(up_bar_style)

    up_bar_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignLeft)
    up_bar_layout.addStretch() 
    up_bar_layout.addWidget(setting_label, alignment=Qt.AlignmentFlag.AlignRight)

    main_layout.addLayout(up_bar_layout)

    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)   
    line.setFrameShadow(QFrame.Shadow.Sunken) 
    line.setStyleSheet("background-color: #ccc; margin-top: 5px; margin-bottom: 20px;")
    main_layout.addWidget(line)

    central_layout = QVBoxLayout()
    central_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
    main_layout.addLayout(central_layout)

    first_message = f"{lpak.get("Some settings are missing", language)}!\n{lpak.get("Let's start the web-based configuration", language)}."
    first_message_label = QLabel(text=first_message)
    first_message_label.setStyleSheet("font: 16pt; margin-bottom: 20px;")
    first_message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    start_config_button = QPushButton(text=lpak.get("Start", language))
    start_config_button.setStyleSheet("""
        QPushButton { background-color: #0078D7; color: white; font: bold 14pt; border-radius: 5px; padding: 10px 20px; }
        QPushButton:hover { background-color: #005A9E; }
    """)
    start_config_button.setFixedWidth(200)
    start_config_button.pressed.connect(show_web_server_info)

    central_layout.addWidget(first_message_label, alignment=Qt.AlignmentFlag.AlignCenter)
    central_layout.addWidget(start_config_button, alignment=Qt.AlignmentFlag.AlignCenter)

    web_signals.finished.connect(show_finished_screen)
    app.aboutToQuit.connect(web_server.shutdown)
    if test_mode_enable():
        root.showMaximized()
    else:
        root.showFullScreen()
    app.exec()


if __name__ == "__main__":
    use_gui_flag = "--no-gui" not in sys.argv
    run_setup(use_gui=use_gui_flag)