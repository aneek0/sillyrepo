# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import asyncio
from wakeonlan import send_magic_packet
from telethon import events
from .. import loader, utils

def register(cb):
    cb(WoLMod())

class WoLMod(loader.Module):
    """Модуль для отправки Wake-on-LAN пакета"""

    strings = {"name": "WoL"}

    async def wolcmd(self, message):
        """.wol
        Отправляет Wake-on-LAN пакет на компьютер.
        """
        mac_address = "18:C0:4D:0F:A6:C3"
        broadcast_ip = "192.168.0.255"

        try:
            send_magic_packet(mac_address, ip_address=broadcast_ip)
            await message.edit("Wake-on-LAN пакет отправлен!")
        except Exception as e:
            await message.edit(f"Ошибка при отправке WoL пакета: {e}")