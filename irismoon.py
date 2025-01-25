version = (2, 2, 8)

# meta developer: @stopxiaomi & @Azu_nyyyyyyaaaaan

import random
from datetime import datetime, timedelta
from telethon import functions
from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class Irismoon(loader.Module):
    """Автофарм в ирисе"""

    strings = {
        "name": "Irismoon",
    }

    def init(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.myid = (await client.get_me()).id
        self.iris = 5434504334

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
    async def moonlightfarm(self, message):
        """Завести таймеры в Iris Moonlight Dyla"""
        await utils.answer(message, "Начинаю установку таймеров...")
        for i in range(100):
         timee = datetime.now()
         hours_to_add = 5.1 * (i + 1)
         schedule_time = timee + timedelta(hours=hours_to_add, minutes=5)
         await self.client.send_message('@iris_moon_bot', "Ферма", schedule=schedule_time)
        await utils.answer(message, "Таймеры успешно установлены!")