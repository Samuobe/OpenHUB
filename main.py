import os
import subprocess
import sys
import configparser
from sys import argv

# Set the base directory to where main.py is located so that all
# relative file paths work correctly regardless of the working directory
# when the script is invoked (e.g. via /usr/bin/open-hub).
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

from config_process import run_setup

def test_mode_enable():    
    return os.path.isfile("test.txt")

if test_mode_enable() or os.path.isfile("AUR"):
    data_path="/var/lib/open-hub/"
else:
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
    command=argv[1]    
except:
    command=None


if command == "start":
    try:
        specific = argv[2]
    except:
        specific = None
    if specific == "station":
        if not check_configuration():
            run_setup()

        files = ["app.py", "back_process/music.py", "back_process/clock.py", "back_process/api.py"]

        processi = []

        for file in files:
            p = subprocess.Popen([sys.executable, file])
            processi.append(p)
            print(f"Started {file} whit PID: {p.pid}")

        try:
            for p in processi:
                p.wait()
        except KeyboardInterrupt:
            print("\nExiting...")
            for p in processi:
                p.terminate() 
    elif specific == "daemon":
        files = ["back_process/music.py", "back_process/clock.py", "back_process/api.py"]

        processi = []

        for file in files:
            p = subprocess.Popen([sys.executable, file])
            processi.append(p)
            print(f"Started {file} whit PID: {p.pid}")

        try:
            for p in processi:
                p.wait()
        except KeyboardInterrupt:
            print("\nExiting...")
            for p in processi:
                p.terminate() 
    elif specific == "help":
        print("main.py start _____")
        print("                |-> station\tStart the full indipendent station whit GUI")
        print("                |-> daemon\tStart all the system except GUI function")
        print("                |-> help\tShow this guide ")
    else:
        print('Error, invalid start arg, use "main.py start help" to see a guide')

elif command == "help":
    print("main.py _____")
    print("          |-> start  ______ \tStart OpenHomeHUB")
    print("          |             |-> station/daemon")
    print("          |")
    print("          |-> help\tShow this guide ")

else:
    print('Error, invalid arg, use "main.py help" to see a guide')