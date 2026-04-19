#!/bin/bash

setup_autostart() {
    echo
    echo "========================================================================"
    echo " OpenHUB systemd service setup"
    echo "========================================================================"

    mkdir -p ~/.config/systemd/user/

    cat <<EOF > ~/.config/systemd/user/openhub.service
[Unit]
Description=OpenHUB - Smart Home Dashboard
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/open-hub start station
Restart=on-failure
RestartSec=5

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
        echo "  open-hub daemon stop disable"
    else
        echo
        echo "Autostart NOT enabled."
        echo "You can enable it later with:"
        echo "  open-hub daemon enable"
    fi

    echo
    echo "Configuration finished."
    echo "To start OpenHUB manually, run:"
    echo "  open-hub daemon start"
    echo
}



echo "Welcome to the OpenHUB installation program!"
echo "What do you want to do?"
echo "1) Install/Update OpenHUB"
echo "2) Uninstall OpenHUB"
read -p "Select an option [1/2/5]: " action

if [[ "$action" == "1" ]]; then
    mkdir open-hub-install
    cd open-hub-install

    PYTHON_PATH=$(which python3)
    echo 
    echo
    read -p "Install the stable version? (y/n): " choice

    if [[ "$choice" =~ ^[Yy]$ ]]; then
        echo "Installing OpenHUB stable..."
        wget https://raw.githubusercontent.com/samuobe/OpenHUB/main/PKGBUILD/PKGBUILD
        makepkg -si
        rm PKGBUILD
        echo "FINISHED!"       
    else
        echo "Installing OpenHUB from main branch (beta)..."       
        wget https://raw.githubusercontent.com/samuobe/OpenHUB/main/PKGBUILD/PKGBUILD-git
        mv PKGBUILD-git PKGBUILD
        makepkg -si        
        rm PKGBUILD
        echo "FINISHED!"        
    fi

    cd ..
    rm -rf open-hub-install
    
    setup_autostart

elif [[ "$action" == "2" ]]; then
    echo
    echo
    echo "Uninstalling OpenHUB..."
    
    systemctl --user stop openhub.service 2>/dev/null
    systemctl --user disable openhub.service 2>/dev/null
    rm -f ~/.config/systemd/user/openhub.service
    systemctl --user daemon-reload
    
    sudo pacman -Rns open-hub
    sudo pacman -Rns open-hub-git
    sudo pacman -Rns open-hub-git-dev
    echo "FINISHED!"
elif [[ "$action" == "5" ]]; then
    mkdir open-hub-install
    cd open-hub-install
    PYTHON_PATH=$(which python3)

    echo "Installing OpenHUB DEV branch..."
    wget https://raw.githubusercontent.com/samuobe/OpenHUB/main/PKGBUILD/PKGBUILD-dev
    mv PKGBUILD-dev PKGBUILD
    makepkg -si
    rm PKGBUILD
    rm /usr/share/arch-store/AUR
    echo "FINISHED!" 

    cd ..
    sudo rm -rf open-hub-install

    setup_autostart
fi

rm -- "$0"