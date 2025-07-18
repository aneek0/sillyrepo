#!/bin/bash

echo -e "\033[2J\033[3;1f"
printf "\n\n\033[1;35mHikka is being installed... ✨\033[0m"

echo -e "\n\n\033[0;96mInstalling base packages...\033[0m"

eval "pkg i git libjpeg-turbo openssl ncurses-utils ffmpeg flac tur-repo -y"

echo -e "\033[0;96mInstalling Python 3.10.15...\033[0m"
eval "pkg i python3.10 -y && update-alternatives --install /data/data/com.termux/files/usr/bin/python3 python3 /data/data/com.termux/files/usr/bin/python3.10 1"

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
eval "cd && git clone https://github.com/coddrago/Hikka && cd Hikka"

echo -e "\033[0;96mSource code downloaded!...\033[0m\n"
printf "\r\033[0;34mInstalling requirements...\e[0m"

eval "pip3.10 install -r requirements.txt --no-cache-dir --no-warn-script-location --disable-pip-version-check --upgrade"

printf "\r\033[K\033[0;32mRequirements installed!\e[0m\n"

if [[ -z "${NO_AUTOSTART}" ]]; then
    printf "\n\r\033[0;34mConfiguring autostart...\e[0m"

    eval "echo '' > ~/../usr/etc/motd &&
    echo 'clear && . <(wget -qO- https://github.com/hikariatama/Hikka/raw/master/banner.sh) && cd ~/Hikka && python3 -m hikka' > ~/.bash_profile"

    printf "\r\033[K\033[0;32mAutostart enabled!\e[0m\n"
fi

echo -e "\033[0;96mStarting Hikka...\033[0m"
echo -e "\033[2J\033[3;1f"

printf "\033[1;32mHikka is starting...\033[0m\n"

eval "python3.10 -m hikka"
