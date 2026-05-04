#!/bin/bash

DEFAULT_INSTALL_DIR="$HOME/.local/share/OpenHUB"
BIN_DIR="$HOME/.local/bin"
LOCAL_BIN="$BIN_DIR/open-hub"
REPO_URL="https://github.com/samuobe/OpenHUB.git"
SCRIPT_PATH="$(pwd)/$0"

# protected files
PROTECTED_FILES=("config.conf" "credential.env" "test.txt")


# Save configurations files
backup_configs() {
    local dir=$1
    local tmp_backup=$(mktemp -d)
    for f in "${PROTECTED_FILES[@]}"; do
        if [ -f "$dir/$f" ]; then
            cp -r "$dir/$f" "$tmp_backup/" 2>/dev/null
        fi
    done
    echo "$tmp_backup"
}

# keep configuraztion
restore_configs() {
    local dir=$1
    local tmp_backup=$2
    for f in "${PROTECTED_FILES[@]}"; do
        if [ -f "$tmp_backup/$f" ]; then
            cp -r "$tmp_backup/$f" "$dir/" 2>/dev/null
        fi
    done
    rm -rf "$tmp_backup"
}

write_info_file() {
    local install_type=$1
    local info_dir=$2
    mkdir -p "$info_dir"
    echo "$install_type" > "$info_dir/instalation_type.info"
}

install_user_bin() {
    local INSTALL_DIR=$1
    local BIN_SRC="$INSTALL_DIR/system_files/open-hub"
    local BIN_DST="$BIN_DIR/open-hub"

    echo "Setting up executable command 'open-hub'..."
    mkdir -p "$BIN_DIR"
    if [ -f "$BIN_SRC" ]; then
        sed "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" "$BIN_SRC" > "$BIN_DST"
    else
        cat <<EOF > "$BIN_DST"
#!/bin/bash
cd "$INSTALL_DIR"
python3 main.py "\$@"
EOF
    fi
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

    pip install --upgrade pip > /dev/null 2>&1
    if [ -f "$REQUIREMENTS_FILE" ]; then
        pip install -r "$REQUIREMENTS_FILE" > /dev/null 2>&1
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
    if [ -f "$SERVICE_FILE_SRC" ]; then
        sed "s|{{INSTALL_DIR}}|$INSTALL_DIR|g; s|{{PYTHON}}|$VENV_DIR/bin/python|g" "$SERVICE_FILE_SRC" > "$SERVICE_FILE_DST"
        systemctl --user daemon-reload

        read -p "Enable OpenHUB at startup? (y/n): " setup_systemd
        if [[ "$setup_systemd" =~ ^[Yy]$ ]]; then
            systemctl --user unmask openhub.service 2>/dev/null
            systemctl --user enable openhub.service 2>/dev/null
            echo "Autostart ENABLED."
        else
            systemctl --user disable openhub.service 2>/dev/null
            echo "Autostart NOT enabled."
        fi
    fi
    
    # Extra services
    systemctl --user enable blueman-applet.service 2>/dev/null
    systemctl --user start blueman-applet.service 2>/dev/null
}

#installation logic
install_openhub() {
    local TARGET_TYPE=$1 # "stable", "main", o "dev"
    local INSTALL_DIR

    echo
    read -p "Enter installation directory (Default: $DEFAULT_INSTALL_DIR): " user_dir
    if [[ -n "$user_dir" ]]; then
        user_dir="${user_dir/#\~/$HOME}"
        if [[ "$user_dir" != /* ]]; then user_dir="$PWD/$user_dir"; fi
        INSTALL_DIR="$user_dir"
    else
        INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    fi

    local INFO_DIR="$INSTALL_DIR/info"

    # Permessi
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR" 2>/dev/null || sudo mkdir -p "$INSTALL_DIR" && sudo chown -R "$USER:$USER" "$INSTALL_DIR"
    fi

    echo "Preparing directory and backing up configurations..."
    local backup_tmp=$(backup_configs "$INSTALL_DIR")

    if [[ "$TARGET_TYPE" == "stable" ]]; then
        # INSTALLAZIONE DA ZIP (STABLE)
        echo "Downloading and extracting the latest STABLE release from GitHub..."
        GITHUB_API="https://api.github.com/repos/Samuobe/OpenHUB/releases/latest"
        ZIP_URL=$(curl -s "$GITHUB_API" | grep '"zipball_url":' | head -1 | cut -d '"' -f4)
        REL_VER=$(curl -s "$GITHUB_API" | grep '"tag_name":' | head -1 | cut -d '"' -f4)

        if [[ -z "$ZIP_URL" || -z "$REL_VER" ]]; then
            echo "Error: Could not determine latest release version."
            exit 1
        fi

        # Pulisci completamente la directory per fare spazio al nuovo ZIP
        find "$INSTALL_DIR" -mindepth 1 -not -path "$INFO_DIR" -not -path "$INSTALL_DIR/venv*" -exec rm -rf {} + 2>/dev/null
        
        TMP_DIR=$(mktemp -d)
        ARCHIVE="$TMP_DIR/openhub.zip"
        curl -sL "$ZIP_URL" -o "$ARCHIVE"

        unzip -q "$ARCHIVE" -d "$TMP_DIR/unzipped"
        TOP_DIR=$(find "$TMP_DIR/unzipped" -mindepth 1 -maxdepth 1 -type d | head -1)
        cp -rfT "$TOP_DIR" "$INSTALL_DIR"
        rm -rf "$TMP_DIR"
        
        echo "OpenHUB installed: $REL_VER"

    else
        # INSTALLAZIONE DA GIT (MAIN / DEV)
        # Se la directory contiene roba ma NON è un repo git (es. provieni da ZIP Stable), dobbiamo svuotare
        if [ -d "$INSTALL_DIR" ] && [ ! -d "$INSTALL_DIR/.git" ]; then
            find "$INSTALL_DIR" -mindepth 1 -not -path "$INFO_DIR" -not -path "$INSTALL_DIR/venv*" -exec rm -rf {} + 2>/dev/null
        fi

        if [ -d "$INSTALL_DIR/.git" ]; then
            echo "Updating existing OpenHUB repository to $TARGET_TYPE branch..."
            cd "$INSTALL_DIR" || exit
            git fetch --all
            # Rimuove le modifiche locali e forza l'allineamento con il branch remoto richiesto
            git reset --hard HEAD
            git clean -fd
            git checkout "$TARGET_TYPE"
            git reset --hard "origin/$TARGET_TYPE"
        else
            echo "Cloning OpenHUB repository ($TARGET_TYPE branch)..."
            git clone -b "$TARGET_TYPE" "$REPO_URL" "$INSTALL_DIR"
            cd "$INSTALL_DIR" || exit
        fi

        COMMIT_VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "NO_GIT")
        echo "OpenHUB installed: $TARGET_TYPE ($COMMIT_VERSION)"
    fi

    echo "Restoring configurations..."
    restore_configs "$INSTALL_DIR" "$backup_tmp"
    write_info_file "$TARGET_TYPE" "$INFO_DIR"

    setup_python_env "$INSTALL_DIR"
    install_user_bin "$INSTALL_DIR"
    setup_autostart "$INSTALL_DIR"

    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo -e "\nWARNING: $BIN_DIR is not in your PATH. Please add it to your ~/.bashrc or ~/.zshrc."
    fi
    echo -e "\nINSTALLATION COMPLETED SUCCESSFULLY!"
}

uninstall_openhub() {
    echo -e "\nUninstalling OpenHUB..."

    systemctl --user stop openhub.service 2>/dev/null
    systemctl --user disable openhub.service 2>/dev/null
    rm -f "$HOME/.config/systemd/user/openhub.service"
    systemctl --user daemon-reload

    INSTALL_DIR_TO_REMOVE="$DEFAULT_INSTALL_DIR"
    if [ -f "$LOCAL_BIN" ]; then
        EXTRACTED_DIR=$(grep -m1 '^cd ' "$LOCAL_BIN" | sed 's/^cd "\(.*\)"$/\1/')
        if [[ -n "$EXTRACTED_DIR" ]]; then
            INSTALL_DIR_TO_REMOVE="$EXTRACTED_DIR"
        fi
    fi

    echo "Removing installation files from $INSTALL_DIR_TO_REMOVE..."
    if [ -d "$INSTALL_DIR_TO_REMOVE" ]; then
        rm -rf "$INSTALL_DIR_TO_REMOVE" 2>/dev/null || sudo rm -rf "$INSTALL_DIR_TO_REMOVE"
    fi

    rm -f "$LOCAL_BIN" 2>/dev/null
    echo "Uninstall FINISHED!"
}

#menu
echo "=========================================="
echo "   Welcome to the OpenHUB Installer!"
echo "=========================================="
echo "A project by Samuele Oberti, author of *Druid of Rats*. Any queries or questions? Get in touch here: https://github.com/samuobe/OpenHUB.git"
echo ""
echo "Select what you want to do:"
echo " 1) Install/Update STABLE  (Latest GitHub Release)"
echo " 2) Install/Update PREVIEW (Main branch - git)"
echo " 3) Uninstall OpenHUB"
echo "=========================================="
read -p "Select an option [1-3]: " action

case $action in
    1) install_openhub "stable" ;;
    2) install_openhub "main" ;;
    5) install_openhub "dev" ;;
    3) uninstall_openhub ;;
    *) echo "Invalid option selected."; exit 1 ;;
esac

#delete script
rm -f "$SCRIPT_PATH"