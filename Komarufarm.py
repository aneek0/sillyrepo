# ---------------------------------------------------------------------------------
#  /\_/\  🌐 This module was loaded through https://t.me/hikkamods_bot
# ( o.o )  🔓 Not licensed.
#  > ^ <   ⚠️ Owner of heta.hikariatama.ru doesn't take any responsibilities or intellectual property rights regarding this script
# ---------------------------------------------------------------------------------
# Name: Iris
# Author: ImSkaiden
# Commands:
# .kfarmon | .kfarmoff | .kfarm | .kprofile
# ---------------------------------------------------------------------------------

version = (0, 0, 2)

# модуль частично не мой | This module is not half mine.
# meta developer: @ImSkaiden

import random
import re
from datetime import timedelta

from telethon import functions
from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class KomaruFarmMod(loader.Module):
    """Для автоматического фарминга карточек в комару кардс"""

    strings = {
        "name": "KomaruFarm",
        "farmon": (
            "<i>✅Отложенка создана, автофарминг запущен, всё начнётся через 20"
            " секунд...</i>"
        ),
        "farmon_already": "<i>Уже запущено</i>",
        "farmoff": "<i>❌Автофарминг остановлен.\n☢️Надюпано:</i> <b>%coins% карточек</b>",
        "farm": "<i>☢️Надюпано:</i> <b>%coins% карточек</b>",
    }

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.myid = (await client.get_me()).id
        self.komaru = 7409912773

    async def kfarmoncmd(self, message):
        """Запустить автофарминг"""
        status = self.db.get(self.name, "status", False)
        if status:
            return await message.edit(self.strings["farmon_already"])
        self.db.set(self.name, "status", True)
        await self.client.send_message(
            self.komaru, "комару", schedule=timedelta(seconds=20)
        )
        await message.edit(self.strings["farmon"])

    async def kfarmoffcmd(self, message):
        """Остановить автофарминг"""
        self.db.set(self.name, "status", False)
        coins = self.db.get(self.name, "coins", 0)
        if coins:
            self.db.set(self.name, "coins", 0)
        await message.edit(self.strings["farmoff"].replace("%coins%", str(coins)))

    async def kfarmcmd(self, message):
        """Вывод кол-ва карточек, добытых этим модулем"""
        coins = self.db.get(self.name, "coins", 0)
        await message.edit(self.strings["farm"].replace("%coins%", str(coins)))

    async def watcher(self, event):
        if not isinstance(event, Message):
            return
        chat = utils.get_chat_id(event)
        if chat != self.komaru:
            return
        status = self.db.get(self.name, "status", False)
        if not status:
            return
        if event.raw_text == "комару":
            return await self.client.send_message(
                self.komaru, "комару", schedule=timedelta(minutes=random.randint(1, 20))
            )
        if event.sender_id != self.komaru:
            return
        if "вы осмотрелись, но не увидели рядом Комару." in event.raw_text:
            time_pattern = r'(\d+)\s+часов\s+(\d+)\s+минут\s+(\d+)\s+секунд'
            match = re.search(time_pattern, event.raw_text)
    
            if match:
                hours, minutes, seconds = map(int, match.groups())
                randelta = random.randint(20, 60)

                delta = timedelta(hours=hours, minutes=minutes, seconds=seconds + randelta)
                sch = (
                await self.client(
                functions.messages.GetScheduledHistoryRequest(self.komaru, 1488))).messages
                await self.client(
            functions.messages.DeleteScheduledMessagesRequest(
                self.komaru, id=[x.id for x in sch]
            )
        )
                return await self.client.send_message(self.komaru, "комару", schedule=delta)
        if "вы осмотрелись вокруг и увидели.." in event.raw_text:
            return self.db.set(
                        self.name,
                        "coins",
                        self.db.get(self.name, "coins", 0) + 1,
                    )

    async def message_q(
        self,
        text: str,
        user_id: int,
        mark_read: bool = False,
        delete: bool = False,
    ):
        """Отправляет сообщение и возращает ответ"""
        async with self.client.conversation(user_id) as conv:
            msg = await conv.send_message(text)
            response = await conv.get_response()
            if mark_read:
                await conv.mark_read()

            if delete:
                await msg.delete()
                await response.delete()

            return response

    @loader.command()
    async def kprofilecmd(self, message):
        """Показывает ваш профиль"""

        bot = "@KomaruCardsBot"
        bags = await self.message_q(
            "профиль",
            bot,
            delete=True,
        )

        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(message, bags.text)