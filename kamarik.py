# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

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