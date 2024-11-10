#!/bin/bash

echo -e "\033[2J\033[3;1f"

echo -e "\033[0;96mInstalling Pillow...\033[0m"

if eval "lscpu | grep Architecture" | grep -qE 'aarch64'; then
    eval 'export LDFLAGS="-L/system/lib64/"'
else
    eval 'export LDFLAGS="-L/system/lib/"'
fi

eval 'export CFLAGS="-I/data/data/com.termux/files/usr/include/" && pip3.10 install Pillow -U --no-cache-dir'

printf "\r\033[K\033[0;32mPillow installed!\e[0m\n"
