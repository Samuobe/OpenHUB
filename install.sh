#!/bin/bash

DEFAULT_INSTALL_DIR="$HOME/.local/share/OpenHUB"
BIN_DIR="$HOME/.local/bin"
LOCAL_BIN="$BIN_DIR/open-hub"

install_user_bin() {
    local INSTALL_DIR=$1
    local BIN_DIR="$HOME/.local/bin"
    local BIN_SRC="$INSTALL_DIR/system_files/open-hub"
    local BIN_DST="$BIN_DIR/open-hub"

    mkdir -p "$BIN_DIR"
    sed "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" "$BIN_SRC" > "$BIN_DST"
    chmod +x "$BIN_DST"
}

setup_python_env() {
    local INSTALL_DIR=$1
    local VENV_DIR="$INSTALL_DIR/venv"
    local REQUIREMENTS_FILE="$INSTALL_DIR/requirements.txt"

    echo "Setting up Python virtual environment..."
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    source "$VENV_DIR/bin/activate"

    pip install --upgrade pip
    if [ -f "$REQUIREMENTS_FILE" ]; then
        echo "Installing dependencies from requirements.txt..."
        pip install -r "$REQUIREMENTS_FILE"
    fi

    deactivate
}

setup_autostart() {
    local INSTALL_DIR=$1
    local VENV_DIR="$INSTALL_DIR/venv"
    local SYSTEMD_DIR="$HOME/.config/systemd/user"
    local SERVICE_FILE_SRC="$INSTALL_DIR/system_files/openhub.service"
    local SERVICE_FILE_DST="$SYSTEMD_DIR/openhub.service"

    mkdir -p "$SYSTEMD_DIR"

    # copia e sostituisci le variabili
    sed "s|{{INSTALL_DIR}}|$INSTALL_DIR|g; s|{{PYTHON}}|$VENV_DIR/bin/python|g" "$SERVICE_FILE_SRC" > "$SERVICE_FILE_DST"

    systemctl --user daemon-reload

    read -p "Enable OpenHUB at startup? (y/n): " setup_systemd
    if [[ "$setup_systemd" =~ ^[Yy]$ ]]; then
        systemctl --user enable openhub.service
        echo "Autostart ENABLED."
    else
        echo "Autostart NOT enabled."
    fi

    setup_python_env "$INSTALL_DIR"
    install_user_bin "$INSTALL_DIR"
    setup_autostart "$INSTALL_DIR"
}

install_dev() {
    echo "Installing OpenHUB DEV version (dev branch)..."
    echo

    local INSTALL_TYPE="dev"

    read -p "Enter installation directory (Default: $DEFAULT_INSTALL_DIR): " user_dir
    local INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    if [[ -n "$user_dir" ]]; then
        user_dir="${user_dir/#\~/$HOME}"
        if [[ "$user_dir" != /* ]]; then
            user_dir="$PWD/$user_dir"
        fi
        INSTALL_DIR="$user_dir"
    fi

    local INFO_DIR="$INSTALL_DIR/info"

    if [ ! -d "$INSTALL_DIR" ]; then
        if ! mkdir -p "$INSTALL_DIR" 2>/dev/null; then
            echo "Requires root privileges to create directory '$INSTALL_DIR'..."
            sudo mkdir -p "$INSTALL_DIR"
            sudo chown -R "$USER:$USER" "$INSTALL_DIR"
        fi
    else
        if [ ! -w "$INSTALL_DIR" ]; then
            echo "Requires root privileges to gain write access to '$INSTALL_DIR'..."
            sudo chown -R "$USER:$USER" "$INSTALL_DIR"
        fi
    fi

    mkdir -p "$BIN_DIR"

    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "Updating existing OpenHUB DEV repository..."
        cd "$INSTALL_DIR" || exit
        git fetch --all
        git checkout dev
        git pull origin dev
    else
        echo "Cloning OpenHUB repository (dev branch)..."
        git clone -b dev https://github.com/samuobe/OpenHUB.git "$INSTALL_DIR"
    fi
    
    setup_python_env "$INSTALL_DIR"
    write_info_file "$INSTALL_TYPE" "$INFO_DIR"

    cd "$INSTALL_DIR"
    COMMIT_VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "NO_GIT")
    echo "OpenHUB DEV version: $COMMIT_VERSION"

    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo "WARNING: $BIN_DIR is not in your PATH. Please add it."
    fi

    common_setup "$LOCAL_BIN"
}

common_setup(){
    local EXEC_PATH=$1
    setup_autostart "$EXEC_PATH"
    systemctl --user enable blueman-applet.service 2>/dev/null
    systemctl --user start blueman-applet.service 2>/dev/null
}

write_info_file() {
    local install_type=$1
    local info_dir=$2
    mkdir -p "$info_dir"
    echo "$install_type" > "$info_dir/instalation_type.info"
    echo "Installation type saved as '$install_type' in $info_dir/instalation_type.info"
}

install_standard() {
    echo "Installing OpenHUB for the current user..."
    echo
    read -p "Do you want to install the STABLE version (last GitHub release) instead of PREVIEW (main branch)? (y/n): " is_stable

    local INSTALL_TYPE="main"
    echo
    read -p "Enter installation directory (Default: $DEFAULT_INSTALL_DIR): " user_dir
    local INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    if [[ -n "$user_dir" ]]; then
        user_dir="${user_dir/#\~/$HOME}"
        if [[ "$user_dir" != /* ]]; then
            user_dir="$PWD/$user_dir"
        fi
        INSTALL_DIR="$user_dir"
    fi
    local INFO_DIR="$INSTALL_DIR/info"

    if [ ! -d "$INSTALL_DIR" ]; then
        if ! mkdir -p "$INSTALL_DIR" 2>/dev/null; then
            echo "Requires root privileges to create directory '$INSTALL_DIR'..."
            sudo mkdir -p "$INSTALL_DIR"
            sudo chown -R "$USER:$USER" "$INSTALL_DIR"
        fi
    else
        if [ ! -w "$INSTALL_DIR" ]; then
            echo "Requires root privileges to gain write access to '$INSTALL_DIR'..."
            sudo chown -R "$USER:$USER" "$INSTALL_DIR"
        fi
    fi

    mkdir -p "$BIN_DIR"

    if [[ "$is_stable" =~ ^[Yy]$ ]]; then
        INSTALL_TYPE="stable"
        echo "Downloading and extracting the latest stable release from GitHub..."
        
        GITHUB_API="https://api.github.com/repos/Samuobe/OpenHUB/releases/latest"
        ZIP_URL=$(curl -s "$GITHUB_API" | grep '"zipball_url":' | head -1 | cut -d '"' -f4)
        REL_VER=$(curl -s "$GITHUB_API" | grep '"tag_name":' | head -1 | cut -d '"' -f4)

        if [[ -z "$ZIP_URL" || -z "$REL_VER" ]]; then
            echo "Error: Could not determine latest release version or download URL."
            exit 1
        fi
        echo "Latest release: $REL_VER ($ZIP_URL)"

        TMP_DIR=$(mktemp -d)
        ARCHIVE="$TMP_DIR/openhub.zip"
        curl -L "$ZIP_URL" -o "$ARCHIVE"

        find "$INSTALL_DIR" -mindepth 1 -not -path "$INFO_DIR" -exec rm -rf {} +

        unzip -q "$ARCHIVE" -d "$TMP_DIR/unzipped"
        TOP_DIR=$(find "$TMP_DIR/unzipped" -mindepth 1 -maxdepth 1 -type d | head -1)
        cp -rfT "$TOP_DIR" "$INSTALL_DIR"

        rm -rf "$TMP_DIR"

        write_info_file "$INSTALL_TYPE" "$INFO_DIR"



        echo "OpenHUB STABLE version installed: $REL_VER"
    else
        if [ -d "$INSTALL_DIR/.git" ]; then
            echo "Updating existing OpenHUB repository in $INSTALL_DIR..."
            cd "$INSTALL_DIR" || exit
            git fetch --all
            git checkout main
            git pull origin main
        else
            echo "Cloning OpenHUB repository (main branch) into $INSTALL_DIR..."
            git clone -b main https://github.com/samuobe/OpenHUB.git "$INSTALL_DIR"
        fi

        write_info_file "$INSTALL_TYPE" "$INFO_DIR"

        cat <<EOF > "$LOCAL_BIN"
#!/bin/bash
cd "$INSTALL_DIR"
python3 main.py "\$@"
EOF
        chmod +x "$LOCAL_BIN"

        cd "$INSTALL_DIR"
        COMMIT_VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "NO_GIT")
        echo "OpenHUB PREVIEW (main) version: $COMMIT_VERSION"
    fi

    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo "WARNING: $BIN_DIR is not in your PATH. Please add it to your ~/.bashrc or ~/.zshrc."
    fi
    setup_python_env "$INSTALL_DIR"
    common_setup "$LOCAL_BIN"
}

echo "Welcome to the OpenHUB installation program!"
echo "What do you want to do?"
echo "1) Install/Update OpenHUB"
echo "2) Uninstall OpenHUB"
read -p "Select an option [1/2]: " action

if [[ "$action" == "1" ]]; then
    install_standard

elif [[ "$action" == "2" ]]; then
    echo
    echo "Uninstalling OpenHUB..."

    systemctl --user stop openhub.service 2>/dev/null
    systemctl --user disable openhub.service 2>/dev/null
    rm -f ~/.config/systemd/user/openhub.service
    systemctl --user daemon-reload

    INSTALL_DIR_TO_REMOVE="$DEFAULT_INSTALL_DIR"
    if [ -f "$LOCAL_BIN" ]; then
        EXTRACTED_DIR=$(grep '^cd ' "$LOCAL_BIN" | sed 's/^cd "\(.*\)"$/\1/')
        if [[ -n "$EXTRACTED_DIR" ]]; then
            INSTALL_DIR_TO_REMOVE="$EXTRACTED_DIR"
        fi
    fi

    echo "Removing installation files from $INSTALL_DIR_TO_REMOVE..."

    if [ -d "$INSTALL_DIR_TO_REMOVE" ]; then
        if ! rm -rf "$INSTALL_DIR_TO_REMOVE" 2>/dev/null; then
            echo "Requires root privileges to remove directory..."
            sudo rm -rf "$INSTALL_DIR_TO_REMOVE"
        fi
    fi

    rm -f "$LOCAL_BIN" 2>/dev/null

    echo "FINISHED!"
elif [[ "$action" == "5" ]]; then
    install_dev
fi

rm -- "$0"