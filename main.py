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
        if not check_configuration():
            run_setup()

        files = ["app.py", "back_process/music.py", "back_process/clock.py", "back_process/api.py"]

        processi = []

        for file in files:
            file_path = os.path.join(script_dir, file)
            # Aggiunto cwd=script_dir per forzare la directory di lavoro del sottoprocesso
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
                
    elif specific == "daemon":
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
        print("main.py start _____")
        print("                |-> station\tStart the full independent station with GUI")
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