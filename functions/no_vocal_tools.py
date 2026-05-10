import os
import requests

class ImmichClient:
    def __init__(self, url, email, password):
        self.url = url
        self.email = email
        self.password = password

        self.session = requests.Session()
        self.token = None

    def login(self):
        r = self.session.post(
            f"{self.url}/api/auth/login",
            json={"email": self.email, "password": self.password}
        )
        r.raise_for_status()

        data = r.json()
        self.token = data.get("accessToken") or data.get("token")

        if not self.token:
            raise RuntimeError(f"Token non trovato: {r.text}")

        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })

    def get_album_list(self):
        r = self.session.get(f"{self.url}/api/albums")
        r.raise_for_status()
        return r.json()

    def find_album_id_by_name(self, name: str):
        albums = self.get_album_list()

        for a in albums:
            if a.get("albumName") == name or a.get("name") == name:
                return a["id"]

        raise RuntimeError(f"Album '{name}' non trovato")

    def list_album_assets(self, album_id: str):
        r = self.session.get(f"{self.url}/api/albums/{album_id}")
        r.raise_for_status()

        data = r.json()
        assets = data.get("assets") or []

        if isinstance(assets, dict) and "items" in assets:
            assets = assets["items"]

        return assets

    def download_asset(self, asset, out_dir="download_album"):
        os.makedirs(out_dir, exist_ok=True)

        asset_id = asset["id"]
        filename = (
            asset.get("originalFileName")
            or asset.get("originalPath", "").split("/")[-1]
            or f"{asset_id}.bin"
        )

        out_path = os.path.join(out_dir, filename)

        r = self.session.get(
            f"{self.url}/api/assets/{asset_id}/original",
            stream=True
        )
        r.raise_for_status()

        with open(out_path, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

        print("Saved:", out_path)

    def download_album(self, album_name: str, out_dir="download_album", videos=False):
        album_id = self.find_album_id_by_name(album_name)
        assets = self.list_album_assets(album_id)

        if not videos:
            assets = [
                a for a in assets
                if (a.get("type") or a.get("assetType") or "").upper() != "VIDEO"
            ]

        print(f"Album '{album_name}' -> {len(assets)} file")

        for a in assets:
            self.download_asset(a, out_dir)

""" COME USARLO
from immich_client import ImmichClient

immich = ImmichClient(
    url="http://localhost:2283",
    email="you@example.com",
    password="yourpassword"
)

immich.login()

# lista album
albums = immich.get_album_list()
print(albums)

# download album
immich.download_album("Vacanze 2025")
"""