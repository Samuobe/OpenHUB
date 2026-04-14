#!/bin/bash

# Funzione per configurare l'avvio automatico (systemd user)
setup_autostart() {
    echo
    echo "========================================================================"
    echo " Do you want to start OpenHUB automatically when you turn on your computer?"
    echo " This will also enable automatic updates in the background."
    echo "========================================================================"
    echo " Type 'y' for YES (Recommended for most users)"
    echo " Type 'n' for NO (You will need to start it manually every time)"
    read -p "Enable automatic startup? (y/n): " setup_systemd

    if [[ "$setup_systemd" =~ ^[Yy]$ ]]; then
        echo "Configuring automatic startup..."
        
        # Crea la cartella per i servizi utente se non esiste
        mkdir -p ~/.config/systemd/user/
        
        # Crea il file del servizio
        cat <<EOF > ~/.config/systemd/user/openhub.service
[Unit]
Description=OpenHUB - Smart Home Dashboard
After=network.target

[Service]
Type=simple
# QUI È DOVE PASSI GLI ARGOMENTI "start station"
ExecStart=/usr/bin/open-hub start station
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

        # Ricarica systemd per leggere il nuovo file
        systemctl --user daemon-reload
        
        # Abilita l'avvio automatico
        systemctl --user enable openhub.service
        
        echo "Automatic startup configured successfully!"
        echo
        
        # Chiede se avviarlo subito
        read -p "Do you want to start OpenHUB right now? (y/n): " start_now
        if [[ "$start_now" =~ ^[Yy]$ ]]; then
            echo "Starting OpenHUB..."
            systemctl --user start openhub.service
            echo "OpenHUB is now running in the background!"
        fi
    else
        echo "Automatic startup skipped. You can always start it manually."
    fi
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
    #sudo rm /usr/share/open-hub-install/AUR

    cd ..
    rm -rf open-hub-install
    
    # Richiama la configurazione systemd dopo l'installazione
    setup_autostart

elif [[ "$action" == "2" ]]; then
    echo
    echo
    echo "Uninstalling OpenHUB..."
    
    # Ferma e disabilita il servizio se esiste prima di disinstallare
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
    
    # Richiama la configurazione systemd dopo l'installazione
    setup_autostart
fi

rm -- "$0"