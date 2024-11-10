#!/bin/bash

echo -e "\033[2J\033[3;1f"

eval "cat ~/Hikka/assets/download.txt"
printf "\n\n\033[1;35mHikka is being installed... ✨\033[0m"

echo -e "\n\n\033[0;96mInstalling base packages...\033[0m"

eval "pkg i git libjpeg-turbo openssl -y"

printf "\r\033[K\033[0;32mPackages ready!\e[0m\n"
echo -e "\033[0;96mInstalling Pillow...\033[0m"

if eval "lscpu | grep Architecture" | grep -qE 'aarch64'; then
    eval 'export LDFLAGS="-L/system/lib64/"'
else
    eval 'export LDFLAGS="-L/system/lib/"'
fi

eval 'export CFLAGS="-I/data/data/com.termux/files/usr/include/" && pip3.10 install Pillow -U --no-cache-dir'

printf "\r\033[K\033[0;32mPillow installed!\e[0m\n"
echo -e "\033[0;96mDownloading source code...\033[0m"

eval "rm -rf ~/Hikka 2>/dev/null"
eval "cd && git clone https://github.com/hikariatama/Hikka && cd Hikka"

echo -e "\033[0;96mSource code downloaded!...\033[0m\n"
