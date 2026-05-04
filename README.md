# OpenHUB

OpenHUB is a Python-based “home hub / station” application with a lot of features powered by "Lattuga Project". It's an opensource alternative to google nest hub or amazon echo show.

https://github.com/user-attachments/assets/98432f7c-97f6-4c82-a0e1-eac1a50140b5

---

## Key features

- **Voice interaction**: wake word listening + voice input + vocal response from Lattuga
- **Widgets**: some default widget that can connect whit your selfhosted data
- **API**: You can integrate the AI and the notify system via API.
- **Bluetooh connection**: For music, or to use external speakers.
- **In-App update**: Upgrade your app from settings.

---

## Installation

### Quick install 
#### First of all! Install the dependencies:
- **Arch**: 
```sudo pacman -S --needed \
  base-devel git curl unzip \
  python python-pip \
  alsa-lib portaudio \
  espeak-ng playerctl \
  vlc mpv \
  xcb-util-cursor noto-fonts-emoji \
  blueman \
  ollama \
  procps-ng systemd
  ```
- **Debian/Ubuntu**:
```sudo apt update
sudo apt install -y \
  git curl unzip \
  python3 python3-pip python3-venv \
  libasound2 libportaudio2 \
  espeak-ng playerctl \
  vlc mpv \
  libxcb-cursor0 fonts-noto-color-emoji \
  blueman \
  udev procps
```

- **Fedora**:
```
sudo dnf install -y \
  git curl unzip \
  python3 python3-pip \
  alsa-lib portaudio \
  espeak-ng playerctl \
  vlc mpv \
  xcb-util-cursor google-noto-emoji-color-fonts \
  blueman \
  procps-ng
```

**NOTE**: At present, the programme has only been tested on Arch! It may or may not work on other distributions; if it doesn’t work, please share any issues you encounter and/or any solutions you find.


#### Run the installer script:

```bash
curl -LO https://raw.githubusercontent.com/Samuobe/OpenHUB/main/install.sh && bash install.sh
```

The installer will:
- install OpenHUB under `~/.local/share/OpenHUB` (or a custom folder)
- create a Python **virtual environment** in `INSTALL_DIR/venv`
- install Python dependencies from `requirements.txt`
- install the `open-hub` launcher into `~/.local/bin`
- optionally configure **systemd user autostart** (`openhub.service`)

You hardly have to do a thing! For the best installation, simply select ‘Stable’ and enable automatic boot when prompted. And then, boom! Restart and you're all set

### Update
You have two options:
- **In-App update**: Open settings and click update. 
- **Re-run the installer**: choose "Install/Update".

### Uninstall
Re-run the installer and choose **Uninstall**.

---

## Usage (CLI)

After installation, use:

```bash
open-hub help
```
To see a guide about the avaible commands.



> Note: DO NOT USE `open-hub start station` modes unless you know what you’re doing. YOU MUST USE `open-hub daemon start`.

---

## Configuration

Set-up is really easy! When you start up, a link will appear; just click on it from one of your devices and fill in the required fields! The second screen will ask how you want to use the AI models; for low-powered computers, we recommend the cloud option – you’ll need to create an Ollama account, which is free. That said, the local option offers greater privacy.

---

## Contributing

Contributions are welcome!

### General workflow
1. Fork the repo
2. Create a feature branch from `dev` (preferred for changes):
   ```bash
   git checkout dev
   git checkout -b feature/my-change
   ```
3. Make changes with clear commits
4. Open a Pull Request targeting **`dev`**

### Contributing in translation
To contribute to the translation, you need to fork the project. Then you need to make a copy of the ‘English.lpak’ file located in the “lpak” subfolder. The file name MUST BE the name of the language in the actual language; for example, the file for Italian is NOT called ‘Italian.lpak’, but MUST BE called ‘Italiano.lpak’. Once you have done this, translate only the right-hand side of each phrase; for example, ‘hello|hello’ would become ‘hello|ciao’ in Italian. DO NOT UNDER ANY CIRCUMSTANCES TOUCH THE FIRST COLUMN. After that, submit a pull request.


### Adding a UI widget/plugin
The app loads UI plugins from:
- `apps/UI/<plugin_name>/manifest.json`

If you add a new widget:
- include a `manifest.json`
- provide the Python entry file and class defined in the manifest
- document enable/disable behavior (the app uses a `status.conf` file with `enable/disable`)

There is an example inclused in the script.

---

## Troubleshooting / Problems

### The app doesn’t start / GUI crashes
1. Check service status:
   ```bash
   open-hub daemon status
   ```
2. Restart it:
   ```bash
   open-hub daemon restart
   ```
3. If it’s a broken install or dependency mismatch, force update:
   ```bash
   open-hub recovery update
   ```

### Missing command: `open-hub`
Ensure `~/.local/bin` is in your `PATH`:
```bash
echo $PATH | tr ':' '\n' | grep -n "\.local/bin"
```
If missing, add to your shell config (e.g. `~/.bashrc` or `~/.zshrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Music widget not working
- Install `playerctl`
- If Bluetooth / MPRIS integration is required, install `mpris-proxy`
- If you use mpv, ensure MPRIS is available and the player is detected

### Text-to-speech not working
Install `espeak-ng` and verify:
```bash
espeak-ng --version
```

### Configuration errors
If OpenHUB complains about configuration:
- ensure `credential.env` exists and is fully filled (no empty fields / `*`)
- ensure `config.conf` exists and has required keys

### Still stuck?
Open an Issue with:
- your OS/distro
- how you installed (stable/main/dev)
- logs from:
  - `open-hub daemon status`
  - any terminal output when running `python3 main.py start station` (if applicable)

---

## License
It’s all yours! Do whatever you like – if you want to quote me, you’d be doing me a huge favour!

---
## Author
My name is Samuele Oberti. If you’d like to support me in another way, search for ‘Druid of Rats’ and follow me on social media – who knows, you might just love my music!
