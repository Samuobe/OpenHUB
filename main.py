import os
import subprocess
import sys
import configparser
from sys import argv
from config_process import run_setup

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

def test_mode_enable():    
    return os.path.isfile("test.txt")

data_path = ""

def check_configuration():
    base_file = "credential_base.env"
    user_file = f"{data_path}credential.env"

    if not os.path.exists(user_file):
        return False

    base_config = configparser.ConfigParser()
    base_config.optionxform = str 
    base_config.read(base_file)

    user_config = configparser.ConfigParser()
    user_config.optionxform = str
    user_config.read(user_file)

    for section in base_config.sections():
        if not user_config.has_section(section):
            return False
            
        for key in base_config.options(section):
            if not user_config.has_option(section, key):
                return False

            val = user_config.get(section, key).strip()
            if val == "":
                return False

    return True

try:
    command = argv[1]    
except IndexError:
    command = None


if command == "start":
    try:
        specific = argv[2]
    except IndexError:
        specific = None
        
    if specific == "station":
        print("###################")
        print("ATTENCTION!!! DON'T USE THIS IF YOU DON'T KNOW WHAT YOU ARE DOING!!!")
        print('USE "open-hub daemon start" TO START OPENHUB')
        print("###################")
        if not check_configuration():
            run_setup()

        files = ["app.py", "back_process/music.py", "back_process/clock.py", "back_process/api.py"]

        processi = []

        for file in files:
            file_path = os.path.join(script_dir, file)
            p = subprocess.Popen([sys.executable, file_path], cwd=script_dir)
            processi.append(p)
            print(f"Started {file} with PID: {p.pid} in {script_dir}")

        try:
            for p in processi:
                p.wait()
        except KeyboardInterrupt:
            print("\nExiting...")
            for p in processi:
                p.terminate() 
                
    elif specific == "core":
        files = ["back_process/music.py", "back_process/clock.py", "back_process/api.py"]

        processi = []

        for file in files:
            file_path = os.path.join(script_dir, file)
            p = subprocess.Popen([sys.executable, file_path], cwd=script_dir)
            processi.append(p)
            print(f"Started {file} with PID: {p.pid} in {script_dir}")

        try:
            for p in processi:
                p.wait()
        except KeyboardInterrupt:
            print("\nExiting...")
            for p in processi:
                p.terminate() 
                
    elif specific == "help":
        print("open-hub start _____")
        print("                |-> station\tStart the full independent station with GUI")
        print("                |-> core\tStart all the system except GUI function")
        print("                |-> help\tShow this guide ")
    else:
        print('Error, invalid start arg, use "main.py start help" to see a guide')

elif command == "daemon":
    try:
        specific = argv[2]
    except IndexError:
        specific = None
    
    if specific == "enable":
        os.system("systemctl --user enable openhub.service")
    elif specific == "disable":
        os.system("systemctl --user disable openhub.service")
    elif specific == "start":
        os.system("systemctl --user start openhub.service")
    elif specific == "stop":
        os.system("systemctl --user stop openhub.service")
    elif specific == "status":
        os.system("systemctl --user status openhub.service")
    elif specific == "restart":
        os.system("systemctl --user restart openhub.service")

    elif specific == "help":
        print("open-hub autostart_____")
        print("                     |-> enable \tEnable OpenHUB at the login of this user")
        print("                     |-> disable \tDisable OpenHUB at the login of this user")
        print("                     |-> status \tee OpenHUB status in background")
        print("                     |-> start \tStart OpenHUB in background")
        print("                     |-> stop \tStop OpenHUB in background")
        print("                     |-> restart \tRestart OpenHUB")
        print("                     |-> help\tShow this guide ")
    else:
        print('Error, invalid autostart arg, use "open-hub autostart help" to see a guide')


elif command == "help":
    print("OpenHUB guide. By: Samuele Oberti")
    print("See: https://github.com/Samuobe/OpenHUB")
    print("")
    print("open-hub _____")
    print("          |-> start  ______ \tStart OpenHomeHUB (DON'T USE THIS IF YOU DON'T KNOW WHAT YOU ARE DOING!)")
    print("          |             |-> station/core")
    print("          |")
    print("          |-> daemon ______\tEnable/Disable Autostart\tStart/Stop/Restart Program in background (USE THIS TO START OPNEHUB)")
    print("          |             |-> enable/disable/start/stop/restart")
    print("          |")
    print("          |-> help\tShow this guide ")
    print("")
    print("PLEASE NOTE!!!!! Don't use *start* to use this program normally, use *daemon*")
    print("")

else:
    print('Error, invalid arg, use "open-hub help" to see a guide')