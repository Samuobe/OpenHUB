import os
import subprocess
import time

already_read_disk = False
vlc_telnet_base = None
vlc_cd_process = None

TELNET_PASSWORD = "ciao"
TELNET_PORT = "4212"

def send_notify(msg):
    print(f"[NOTIFIY] {msg}")

def start_telnet_base():
    global vlc_telnet_base
    if vlc_telnet_base is None:
        print("Starting vlc base telnet...")
        cmd = [
            "cvlc", 
            "-I", "dummy", 
            "--extraintf=telnet,mpris", 
            f"--telnet-password={TELNET_PASSWORD}", 
            f"--telnet-port={TELNET_PORT}"
        ]
        vlc_telnet_base = subprocess.Popen(cmd)
        send_notify("Telnet base activated")

def stop_telnet_base():
    global vlc_telnet_base
    if vlc_telnet_base:
        vlc_telnet_base.terminate()
        try:
            vlc_telnet_base.wait(timeout=5)
        except Exception:
            pass
        vlc_telnet_base = None
        send_notify("Telnet base terminated")

def start_cd():
    global vlc_cd_process
    
    print("Stop other music... staring cd")
    os.system("killall mpv")
    stop_telnet_base()
    os.system("killall -9 vlc cvlc")
    time.sleep(0.5)
    
    cmd = [
        "mpv",
        "--no-video",
        "cdda://", 
        "--cdrom-device=/dev/sr0"
    ]
    vlc_cd_process = subprocess.Popen(cmd)
    vlc_cd_process = subprocess.Popen(cmd)
    send_notify("CD in reproduction")

def stop_cd():
    global vlc_cd_process
    if vlc_cd_process:
        vlc_cd_process.terminate()
        try:
            vlc_cd_process.wait(timeout=5)
        except Exception:
            pass
        vlc_cd_process = None
        send_notify("CD stopped")

def check_cd_inserted():
    global already_read_disk
    cd_device = "/dev/sr0"

    if not os.path.exists(cd_device):
        if already_read_disk:
            send_notify("CD removed!")
            stop_cd()
            start_telnet_base()
            already_read_disk = False
        return

    try:
        result = subprocess.run(
            ["udevadm", "info", "--query=property", "--name=sr0"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        output = result.stdout
        has_media = "ID_CDROM_MEDIA=1" in output

        if has_media and not already_read_disk:
            send_notify("CD found - Starting it...")
            already_read_disk = True
            start_cd()
        elif not has_media and already_read_disk:
            send_notify("CD removed")
            stop_cd()
            start_telnet_base()
            already_read_disk = False

    except Exception as e:
        send_notify(f"Errore: {e}")

def main_loop():
    print("Monitoring cd")
    start_telnet_base()  
    while True:
        check_cd_inserted()
        time.sleep(2)

if __name__ == "__main__":
    main_loop()