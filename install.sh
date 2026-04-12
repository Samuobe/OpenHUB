#!/bin/bash


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

elif [[ "$action" == "2" ]]; then
    echo
    echo
    echo "Uninstalling OpenHUB..."
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
fi



rm -- "$0"
