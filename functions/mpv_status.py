import subprocess

def is_mpv_running():
    try:
        # pgrep cerca un processo che si chiama esattamente "mpv"
        result = subprocess.run(["pgrep", "-x", "mpv"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

