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

data_path = ""

# Leggi la configurazione iniziale per la lingua preservando il case-sensitive
config_main = configparser.ConfigParser()
config_main.optionxform = str
if os.path.isfile("config.conf"):
    config_main.read("config.conf")
language = config_main.get("User data", "Language") if config_main.has_section("User data") else "English"

config_file = f"{data_path}credential.env"

app_state = {
    "sections_to_configure": [],
    "needs_ui": False
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
        "keys": ["SUBSONIC_URL", "SUBSONIC_USERNAME", "SUBSONIC_PASSWORD", "ListenBrainz_key"],
        "optional": True
    }
]

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

def get_base_html_style():
    return """
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h2 { color: #333; border-bottom: 2px solid #0078D7; padding-bottom: 5px; }
        label { font-weight: bold; display: block; margin-top: 10px; }
        input[type="text"], input[type="password"], select { width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        .input-group { display: flex; align-items: center; margin-top: 5px; }
        .input-group input { margin-top: 0; }
        .toggle-btn { margin-left: 10px; padding: 8px 12px; cursor: pointer; border: 1px solid #ccc; border-radius: 4px; background: #eee; font-size: 16px; }
        .toggle-btn:hover { background: #ddd; }
        .btn { display: block; width: 100%; background: #0078D7; color: white; padding: 10px; border: none; border-radius: 5px; font-size: 16px; margin-top: 20px; cursor: pointer; }
        .btn:hover { background: #005A9E; }
        .btn-success { background: #28A745; }
        .btn-success:hover { background: #218838; }
        .optional { color: #888; font-size: 12px; font-weight: normal; }
        .guide-box { background-color: #e7f3fe; border-left: 4px solid #0078D7; padding: 10px; margin-bottom: 15px; font-size: 14px; color: #333; }
        .radio-group { margin-top: 10px; }
        .radio-group label { font-weight: normal; display: inline-block; margin-right: 15px; }
    </style>
    """

class SetupHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            # PAGINA 1: SELEZIONE LINGUA
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            # Leggi dinamicamente le lingue dalla cartella lpak
            available_languages = []
            lpak_dir = "lpak"
            if os.path.exists(lpak_dir) and os.path.isdir(lpak_dir):
                for filename in os.listdir(lpak_dir):
                    if os.path.isfile(os.path.join(lpak_dir, filename)):
                        lang_name = os.path.splitext(filename)[0]
                        available_languages.append(lang_name)
            
            if not available_languages:
                available_languages = ["English"]
            
            available_languages.sort()

            options_html = ""
            for lang in available_languages:
                selected_attr = "selected" if language == lang else ""
                options_html += f'<option value="{lang}" {selected_attr}>{lang}</option>\n'
            
            html = f"""
            <html>
            <head>
                <title>{lpak.get("Language Setup - OpenHomeHUB", language)}</title>
                {get_base_html_style()}
            </head>
            <body>
                <div class="container">
                    <h1 style="text-align: center; color: #0078D7;">{lpak.get("Language Selection", language)}</h1>
                    <form method="POST" action="/main_setup">
                        <label>{lpak.get("Select your language:", language)}</label>
                        <select name="language" required>
                            {options_html}
                        </select>
                        <button type="submit" class="btn">{lpak.get("Continue", language)}</button>
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
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        parsed_data = urllib.parse.parse_qs(post_data)

        if self.path == "/main_setup":
            # PAGINA 2: CONFIGURAZIONE PRINCIPALE
            global language
            if "language" in parsed_data:
                language = parsed_data["language"][0]
            
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()

            env_config = configparser.ConfigParser()
            env_config.optionxform = str
            if os.path.isfile(config_file):
                env_config.read(config_file)

            # Vai SEMPRE a /ai_setup a prescindere
            html = f"""
            <html>
            <head>
                <title>{lpak.get("Setup OpenHomeHUB", language)}</title>
                {get_base_html_style()}
                <script>
                    function togglePassword(inputId) {{
                        var input = document.getElementById(inputId);
                        if (input.type === "password") {{
                            input.type = "text";
                        }} else {{
                            input.type = "password";
                        }}
                    }}
                </script>
            </head>
            <body>
                <div class="container">
                    <h1 style="text-align: center; color: #0078D7;">{lpak.get("Setup OpenHomeHUB", language)}</h1>
                    <form method="POST" action="/ai_setup">
                        <input type="hidden" name="language" value="{language}">
            """
            
            if not app_state["sections_to_configure"]:
                html += f"<p style='text-align: center; color: green; font-weight: bold;'>{lpak.get('Network settings are already configured.', language)}</p>"

            for section in app_state["sections_to_configure"]:
                sec_name = section["name"]
                is_optional = section["optional"]
                
                opt_text = f" ({lpak.get('Optional, leave blank to skip', language)})" if is_optional else f" ({lpak.get('Required', language)})"
                html += f"<h2>{sec_name}<span class='optional'>{opt_text}</span></h2>"
                
                if sec_name == "Home Assistant":
                    html += f"""
                    <div class="guide-box">
                        <b>{lpak.get("Home Assistant Token Guide", language)}:</b><br>
                        1. {lpak.get("Open your Home Assistant in your browser", language)}.<br>
                        2. {lpak.get("Click on your", language)} <b>{lpak.get("Profile", language)}</b> ({lpak.get("Bottom left", language).lower()}).<br>
                        3. {lpak.get("Go to the page", language)} <b>{lpak.get("Security", language)}</b> ({lpak.get("At the top", language).lower()}).<br>
                        4. {lpak.get("Scroll to the bottom of the section", language)} <b>{lpak.get("Long-term tokens", language)}</b>. {lpak.get("Than click", language)} <i>{lpak.get("Create token", language)}</i>.<br>
                        5. {lpak.get("Copy the very long token and paste it below!", language)}
                    </div>
                    """
                
                for key in section["keys"]:
                    is_secret = "password" in key.lower() or "token" in key.lower()
                    input_type = "password" if is_secret else "text"
                    req_attr = "" if is_optional else "required"
                    input_id = f"input_{sec_name}_{key}".replace(" ", "_").replace("-", "_")

                    current_value = ""
                    if env_config.has_option(sec_name, key):
                        val = env_config.get(sec_name, key).strip()
                        if val != "" and val != "-":
                            current_value = val.replace('"', '&quot;') 
                    
                    html += f"<label>{key}</label>"

                    if is_secret:
                        html += f"""
                        <div class="input-group">
                            <input type="{input_type}" id="{input_id}" name="{sec_name}|{key}" value="{current_value}" {req_attr}>
                            <button type="button" class="toggle-btn" onclick="togglePassword('{input_id}')" title="Show/Hide">👁️</button>
                        </div>
                        """
                    else:
                        html += f"<input type='{input_type}' id='{input_id}' name='{sec_name}|{key}' value='{current_value}' {req_attr}>"
            
            html += f"""
                        <button type="submit" class="btn">{lpak.get("Continue to AI Setup", language)}</button>
                    </form>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))

        elif self.path == "/ai_setup":
            # PAGINA 3: CONFIGURAZIONE IA OLLAMA (CHIESTA SEMPRE!)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()

            hidden_inputs = ""
            for key, values in parsed_data.items():
                val = values[0].replace('"', '&quot;')
                hidden_inputs += f'<input type="hidden" name="{key}" value="{val}">\n'

            html = f"""
            <html>
            <head>
                <title>{lpak.get("AI Configuration - OpenHomeHUB", language)}</title>
                {get_base_html_style()}
                <script>
                    function toggleAI() {{
                        var mode = document.querySelector('input[name="ai_mode"]:checked').value;
                        if (mode === 'online') {{
                            document.getElementById('online_section').style.display = 'block';
                            document.getElementById('offline_section').style.display = 'none';
                        }} else {{
                            document.getElementById('online_section').style.display = 'none';
                            document.getElementById('offline_section').style.display = 'block';
                        }}
                    }}
                </script>
            </head>
            <body onload="toggleAI()">
                <div class="container">
                    <h1 style="text-align: center; color: #0078D7;">{lpak.get("AI Setup (Ollama)", language)}</h1>
                    <form method="POST" action="/save">
                        {hidden_inputs}
                        
                        <p><b>{lpak.get("Online AI version is strongly recommended, especially for slower computers.", language)}</b></p>
                        
                        <div class="radio-group">
                            <label><input type="radio" name="ai_mode" value="online" checked onchange="toggleAI()"> {lpak.get("Online AI:", language).replace(":", "")}</label>
                            <label><input type="radio" name="ai_mode" value="offline" onchange="toggleAI()"> {lpak.get("Offline AI:", language).replace(":", "")}</label>
                        </div>

                        <div id="online_section" class="guide-box" style="margin-top: 15px;">
                            <p><b>{lpak.get("Online AI:", language)}</b> {lpak.get("This mode allows you to use Cloud AI without downloading it locally.", language)}</p>
                            <p>{lpak.get("You must be authenticated on Ollama to run Cloud models. Click the link below to authenticate, then return here and click Continue.", language)}</p>
                            <a href="https://ollama.com/connect?name=Laptop4&key=c3NoLWVkMjU1MTkgQUFBQUMzTnphQzFsWkRJMU5URTVBQUFBSVByL2NzUXU2T1ljRmtqV29BZjgxWGJQQk5wdjNZOEVKRUd5TzBEV3FVR1I" target="_blank" style="color: #0078D7; font-weight: bold;">{lpak.get("[+] Click here to login to Ollama (Cloud)", language)}</a>
                        </div>

                        <div id="offline_section" class="guide-box" style="margin-top: 15px; display: none;">
                            <p><b>{lpak.get("Offline AI:", language)}</b> {lpak.get("A locally downloaded and running model will be used.", language)}</p>
                            <p><i>{lpak.get("The default model 'llama3' will be saved in the configuration. You can change it later.", language)}</i></p>
                            <input type="hidden" name="ai_model" value="llama3">
                        </div>

                        <button type="submit" class="btn btn-success">{lpak.get("Save configuration", language)}</button>
                    </form>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))

        elif self.path == "/save":
            # SALVATAGGIO FINALE DI TUTTI I FILE
            
            config_c = configparser.ConfigParser()
            config_c.optionxform = str
            
            if os.path.isfile("config.conf"):
                config_c.read("config.conf")
                
            if not config_c.has_section("User data"):
                config_c.add_section("User data")
                
            # Salva Lingua
            config_c.set("User data", "Language", parsed_data.get("language", ["English"])[0])

            # Salva AI_model (ora garantito dalla presenza del modulo AI_setup)
            ai_mode = parsed_data.get("ai_mode", ["online"])[0]
            if ai_mode == "offline":
                config_c.set("User data", "AI_model", parsed_data.get("ai_model", ["llama3"])[0])
            else:
                config_c.set("User data", "AI_model", "ministral-3:14b-cloud")
            
            with open("config.conf", "w") as f:
                config_c.write(f)

            # 2. Salva le credenziali in credential.env
            env_config = configparser.ConfigParser()
            env_config.optionxform = str
            if os.path.isfile(config_file):
                env_config.read(config_file)
            
            for section in app_state["sections_to_configure"]:
                sec_name = section["name"]
                if not env_config.has_section(sec_name):
                    env_config.add_section(sec_name)
                
                for key in section["keys"]:
                    form_key = f"{sec_name}|{key}"
                    if form_key in parsed_data:
                        val = parsed_data.get(form_key, [""])[0].strip()
                        
                        if val == "" and section["optional"]:
                            val = "-"
                            
                        env_config.set(sec_name, key, val)

            with open(config_file, 'w') as f:
                env_config.write(f)
                
            self.send_response(303)
            self.send_header("Location", "/success")
            self.end_headers()
            
            web_signals.finished.emit()

def start_web_server():
    server = HTTPServer(('0.0.0.0', WEB_PORT), SetupHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def prepare_config_state(force_all=False):
    env_config = configparser.ConfigParser()
    env_config.optionxform = str
    if os.path.isfile(config_file):  
        env_config.read(config_file)
        
    app_state["sections_to_configure"] = []
    
    # Controlla se l'AI_model in config.conf è configurato
    config_c = configparser.ConfigParser()
    config_c.optionxform = str
    ai_missing = False
    if os.path.isfile("config.conf"):
        config_c.read("config.conf")
        if not config_c.has_option("User data", "AI_model"):
            ai_missing = True
    else:
        ai_missing = True

    has_missing_sections = False
    for section in CONFIG_SCHEMA:
        sec_name = section["name"]
        needs_config = force_all 
        
        if not force_all:
            if not env_config.has_section(sec_name):
                needs_config = True
            else:
                for key in section["keys"]:
                    if not env_config.has_option(sec_name, key):
                        needs_config = True
                        break
                    
                    val = env_config.get(sec_name, key).strip()
                    if val == "" or val == "-":  
                        needs_config = True
                        break
                    
        if needs_config:
            app_state["sections_to_configure"].append(section)
            has_missing_sections = True
            
    # Attiviamo l'interfaccia se forzato, se mancano le credenziali, OPPURE se manca l'IA
    app_state["needs_ui"] = force_all or has_missing_sections or ai_missing


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
    
    msg = QLabel(f"{lpak.get('To fill in the missing fields, log in via your browser', language)}:")
    msg.setStyleSheet("font: 14pt; margin-bottom: 10px;")
    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    url_msg = QLabel(f"http://{ip_address}:{WEB_PORT}")
    url_msg.setStyleSheet("font: bold 24pt; color: #0078D7; margin-bottom: 20px;")
    url_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    wait_msg = QLabel(f"{lpak.get('Pending completion from the webpage', language)}...")
    wait_msg.setStyleSheet("font: italic 12pt; color: #666;")
    wait_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

    central_layout.addWidget(msg, alignment=Qt.AlignmentFlag.AlignCenter)
    central_layout.addWidget(url_msg, alignment=Qt.AlignmentFlag.AlignCenter)
    central_layout.addWidget(wait_msg, alignment=Qt.AlignmentFlag.AlignCenter)

def show_finished_screen():
    setting_label.setText(lpak.get("Completed", language))
    clear_layout(central_layout)

    msg = QLabel(f"{lpak.get('Configuration completed successfully', language)}!\n{lpak.get('All data has been saved', language)}.")
    msg.setStyleSheet("font: bold 16pt; margin-bottom: 20px; color: #28A745;")
    msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    close_btn = QPushButton(lpak.get("Close and continue", language))
    close_btn.setStyleSheet("""
        QPushButton { background-color: #0078D7; color: white; font: bold 14pt; border-radius: 5px; padding: 10px 20px; }
        QPushButton:hover { background-color: #005A9E; }
    """)
    close_btn.setFixedWidth(200)
    close_btn.clicked.connect(root.close) 

    central_layout.addWidget(msg, alignment=Qt.AlignmentFlag.AlignCenter)
    central_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)


def run_setup(use_gui=True, force=False):
    global root, central_layout, setting_label
    
    prepare_config_state(force_all=force)
    
    # Se tutto è perfettamente configurato (Credenziali e AI) e non stiamo forzando, esce
    if not app_state["needs_ui"]:
        print("Everything is already configured")
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

    app = QApplication.instance()
    if not app:
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

    title_label = QLabel(text=f"{lpak.get('Welcome', language)}")
    setting_label = QLabel(text=f"{lpak.get('Home', language)}")
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

    msg_part1 = lpak.get("Some settings are missing" if not force else "Configuration restarted", language)
    msg_part2 = lpak.get("Let's start the web-based configuration", language)
    first_message = f"{msg_part1}!\n{msg_part2}."
    
    first_message_label = QLabel(text=first_message)
    first_message_label.setStyleSheet("font: 16pt; margin-bottom: 20px;")
    first_message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    start_config_button = QPushButton(text=lpak.get("Start", language))
    start_config_button.setStyleSheet("""
        QPushButton { background-color: #0078D7; color: white; font: bold 14pt; border-radius: 5px; padding: 10px 20px; }
        QPushButton:hover { background-color: #005A9E; }
    """)
    start_config_button.setFixedWidth(200)
    start_config_button.clicked.connect(show_web_server_info)

    central_layout.addWidget(first_message_label, alignment=Qt.AlignmentFlag.AlignCenter)
    central_layout.addWidget(start_config_button, alignment=Qt.AlignmentFlag.AlignCenter)

    web_signals.finished.connect(show_finished_screen)
    app.aboutToQuit.connect(web_server.shutdown)
    if test_mode_enable():
        root.showMaximized()
    else:
        root.showFullScreen()
    
    app.exec()


def restart_configuration(use_gui=True):
    run_setup(use_gui=use_gui, force=True)


if __name__ == "__main__":
    use_gui_flag = "--no-gui" not in sys.argv
    run_setup(use_gui=use_gui_flag)