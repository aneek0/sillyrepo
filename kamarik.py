# ---------------------------------------------------------------------------------
#  /\_/\  🌐 This module was loaded through https://t.me/hikkamods_bot
# ( o.o )  🔐 Licensed under the GNU AGPLv3.
#  > ^ <   ⚠️ Owner of heta.hikariatama.ru doesn't take any responsibilities or intellectual property rights regarding this script
# ---------------------------------------------------------------------------------
# Name: kamarik
# Author: marble team
# Commands:
# .kamar | .kamarik
# ---------------------------------------------------------------------------------

# █ █ █ █▄▀ ▄▀█ █▀▄▀█ █▀█ █▀█ █ █
# █▀█ █ █ █ █▀█ █ ▀ █ █▄█ █▀▄ █▄█

# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html
# 👤 https://t.me/hikamoru

from .. import loader, utils
import asyncio

class kamarik(loader.Module):
    """"""

    strings = {"name": "kamarik"}

    async def kamarikcmd(self, message):
        """Аўта камарік раз в 4 гадзіны"""
        self.set("kamarik", True)
        while self.get("kamarik"):
            await message.reply("камар")
            await asyncio.sleep(14400)
        await message.delete()

    async def kamarcmd(self, message):
        """Аўта камар раз в 3 гадзіны"""
        self.set("kamar", True)
        while self.get("kamar"):
            await message.reply("Комару")
            await asyncio.sleep(10800)
        await message.delete()

    async def watcher(self, message):
        if not getattr(message, "out", False):
            return

        if message.raw_text.lower() == "камар стоп":
            self.set("kamarik", False)
            self.set("kamar", False)
            await utils.answer(message, "<b>Фарм комаріков остановлен.</b>")
            await message.delete()
                   
        if message.raw_text.lower() in [".kamarik", ".kamar"]:
            await message.delete()