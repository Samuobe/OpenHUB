import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.no_vocal_tools import ImmichClient
import glob
import time
import configparser

login = False
photo_dir = "custom/images/immich"
album_name = "OpenHUB"
data_path = ""

#Load config
config =configparser.ConfigParser()
config.optionxform = str
config.read(f"{data_path}credential.env")
immich_url = config.get("Immich", "Url")
immich_mail = config.get("Immich", "Email")
immich_password = config.get("Immich", "Password")

#print("URL: ", immich_url)
#print("User: ", immich_mail)
#print("Pass: ", immich_password)

while not login:
    try:
        immich = ImmichClient(
            immich_url,
            immich_mail,
            immich_password
        )

        immich.login()
        login = True
        print("Immiche logged correctly")
        
    except Exception as e:
        print("Error during immich login: ", e)
    time.sleep(5)

while True: 
    try:
        local_files = glob.glob(f"{photo_dir}/*")

        local_files = [os.path.basename(f) for f in local_files]

        remote_files = immich.get_album_filenames(album_name)

        missing = [f for f in remote_files if f not in local_files]

        #print("Da scaricare:", missing)

        album_id = immich.find_album_id_by_name(album_name)
        assets = immich.list_album_assets(album_id)

        to_remove = set(local_files) - set(remote_files)

        for asset in assets:
            filename = (
                asset.get("originalFileName")
                or asset.get("originalPath", "").split("/")[-1]
            )

            if filename in missing:
                immich.download_asset(asset, photo_dir)

        for asset in to_remove:
            #print("Removed: ", asset)
            os.remove(f"{photo_dir}/{asset}")
    except Exception as e:
        print("Immich erro: ", e)


    time.sleep(10)



