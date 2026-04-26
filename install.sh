#!/bin/bash

INSTALL_DIR="$HOME/.local/share/OpenHUB"
BIN_DIR="$HOME/.local/bin"
LOCAL_BIN="$BIN_DIR/open-hub"
INFO_DIR="$HOME/.local/share/OpenHUB/info"

setup_autostart() {
    local EXEC_PATH=$1

    echo
    echo "========================================================================"
    echo " OpenHUB systemd service setup"
    echo "========================================================================"

    mkdir -p ~/.config/systemd/user/

    cat <<EOF > ~/.config/systemd/user/openhub.service
[Unit]
Description=OpenHUB - Smart Home Dashboard
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=${EXEC_PATH} start station
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload

    echo "Service file created successfully."
    echo
    echo "Do you want to enable OpenHUB at startup?"
    echo "Type 'y' for YES"
    echo "Type 'n' for NO"
    read -p "Enable automatic startup? (y/n): " setup_systemd

    if [[ "$setup_systemd" =~ ^[Yy]$ ]]; then
        systemctl --user enable openhub.service
        echo
        echo "Autostart ENABLED."
        echo "To disable and stop it later, use:"
        echo "  ${EXEC_PATH} daemon stop disable"
    else
        echo
        echo "Autostart NOT enabled."
        echo "You can enable it later with:"
        echo "  ${EXEC_PATH} daemon enable"
    fi

    echo
    echo "Configuration finished."
    echo "To start OpenHUB manually, run:"
    echo "  ${EXEC_PATH} daemon start"
    echo
}

common_setup(){
    local EXEC_PATH=$1
    setup_autostart "$EXEC_PATH"
    systemctl --user enable blueman-applet.service 2>/dev/null
    systemctl --user start blueman-applet.service 2>/dev/null
}

write_info_file() {
    local install_type=$1
    mkdir -p "$INFO_DIR"
    echo "$install_type" > "$INFO_DIR/instalation_type.info"
    echo "Installation type saved as '$install_type' in $INFO_DIR/instalation_type.info"
}

install_standard() {
    echo "Installing OpenHUB locally for the current user..."
    
    echo
    read -p "Do you want to install the STABLE version instead of PREVIEW (main)? (y/n): " is_stable
    
    local branch_name="main"
    local type_string="main"
    
    if [[ "$is_stable" =~ ^[Yy]$ ]]; then
        branch_name="stable"
        type_string="stable"
    fi

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"

    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "Updating existing OpenHUB repository..."
        cd "$INSTALL_DIR"
        git fetch --all
        git checkout "$branch_name"
        git pull origin "$branch_name"
    else
        echo "Cloning OpenHUB repository (Branch: $branch_name)..."
        git clone -b "$branch_name" https://github.com/samuobe/OpenHUB.git "$INSTALL_DIR"
    fi


    write_info_file "$type_string"

    cat <<EOF > "$LOCAL_BIN"
#!/bin/bash
cd "$INSTALL_DIR"
python3 main.py "\$@"
EOF
    chmod +x "$LOCAL_BIN"

    echo "Local installation finished! Executable created at $LOCAL_BIN"
    
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo "WARNING: $BIN_DIR is not in your PATH. Please add it to your ~/.bashrc or ~/.zshrc."
    fi

    common_setup "$LOCAL_BIN"
}

install_pkgbuild() {
    local version_type=$1
    mkdir -p open-hub-install
    cd open-hub-install

    PYTHON_PATH=$(which python3)

    echo "Installing OpenHUB via PKGBUILD ($version_type)..."
    if [ "$version_type" == "stable" ]; then
        wget -O PKGBUILD https://raw.githubusercontent.com/samuobe/OpenHUB/main/PKGBUILD/PKGBUILD
        write_info_file "pkgbuild"
    elif [ "$version_type" == "beta" ]; then
        wget -O PKGBUILD https://raw.githubusercontent.com/samuobe/OpenHUB/main/PKGBUILD/PKGBUILD-git
        write_info_file "pkgbuild"
    elif [ "$version_type" == "dev" ]; then
        wget -O PKGBUILD https://raw.githubusercontent.com/samuobe/OpenHUB/main/PKGBUILD/PKGBUILD-dev
        write_info_file "dev"
    fi
    
    makepkg -sif
    rm PKGBUILD
    cd ..
    rm -rf open-hub-install
    
    echo "PKGBUILD installation finished!"
    common_setup "/usr/bin/open-hub"
}

echo "Welcome to the OpenHUB installation program!"
echo "What do you want to do?"
echo "1) Install/Update OpenHUB"
echo "2) Uninstall OpenHUB"
read -p "Select an option [1/2]: " action

if [[ "$action" == "1" ]]; then
    if [ -f "/etc/arch-release" ]; then
        echo
        echo "Arch Linux detected."
        echo "Do you want to use the standard local user installation (Recommended) or the global PKGBUILD?"
        echo "1) Standard Local Install (Recommended)"
        echo "2) Global PKGBUILD"
        read -p "Choose installation method [1/2] (Default: 1): " arch_method
        
        if [[ -z "$arch_method" || "$arch_method" == "1" ]]; then
            install_standard
        else
            echo 
            read -p "Install the stable version? (y/n): " choice
            if [[ "$choice" =~ ^[Yy]$ ]]; then
                install_pkgbuild "stable"
            else
                install_pkgbuild "beta"
            fi
        fi
    else
        echo "Non-Arch Linux system detected. Using standard local installation."
        install_standard
    fi

elif [[ "$action" == "2" ]]; then
    echo
    echo
    echo "Uninstalling OpenHUB..."
    
    systemctl --user stop openhub.service 2>/dev/null
    systemctl --user disable openhub.service 2>/dev/null
    rm -f ~/.config/systemd/user/openhub.service
    systemctl --user daemon-reload
    
    rm -rf "$INSTALL_DIR" 2>/dev/null
    rm -f "$LOCAL_BIN" 2>/dev/null
    rm -rf "$INFO_DIR" 2>/dev/null

    if command -v pacman >/dev/null 2>&1; then
        sudo pacman -Rns open-hub 2>/dev/null
        sudo pacman -Rns open-hub-git 2>/dev/null
        sudo pacman -Rns open-hub-git-dev 2>/dev/null
    fi

    echo "FINISHED!"

elif [[ "$action" == "5" ]]; then
    if [ -f "/etc/arch-release" ]; then
        install_pkgbuild "dev"
        sudo rm -f /usr/share/arch-store/AUR 2>/dev/null
    else
        echo "Error: Option 5 (DEV branch via PKGBUILD) is only supported on Arch Linux."
    fi
fi

rm -- "$0"