#meta developer: @blazeftg / @wsinfo
version = (1, 0, 0)

import asyncio

from telethon import functions
from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class GigaChatMod(loader.Module):
    """
    Бесплатный модуль
    """

    strings = {
        "name": "Giga",
        "loading": "🔄 Uno momento...",
        "no_args": "🚫 Args!",
        "start_text": "<b>🤖 AuthorAi:</b>\n",
        "context_text": "❕ Nice work",
    }

    def init(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.gpt_free = "@gigachat_bot"

    async def message_q(
        self,
        text: str,
        user_id: int,
        mark_read: bool = False,
        delete: bool = False,
        ignore_answer: bool = False,
    ):
        """Отправляет сообщение и возращает ответ"""
        async with self.client.conversation(user_id) as conv:
            msg = await conv.send_message(text)
            while True:
                await asyncio.sleep(1)
                response = await conv.get_response()
                if mark_read:
                    await conv.mark_read()
                if delete:
                    await msg.delete()
                    await response.delete()
                if ignore_answer:
                    return response
                if "Классный запрос," in response.text:
                    continue
                if "Запрос принят," in response.text:
                    continue
                return response

    async def gigacmd(self, message: Message):
        """
        {text} - обработать текст через giga
        """
        args = utils.get_args_raw(message)

        if not args:
            return await utils.answer(message, self.strings["no_args"])
        await utils.answer(message, self.strings["loading"])

        response = await self.message_q(
            args, self.gpt_free, mark_read=True, delete=False, ignore_answer=False
        )

        text = self.strings["start_text"] + response.text.replace(
            "/context", "<code>.contextgpt</code>"
        )

        return await utils.answer(message, text)

    async def gclearcmd(self, message: Message):
        """
        - сбросить диалог и начать новый
        """
        await self.message_q(
            "/restart", self.gpt_free, mark_read=True, delete=False, ignore_answer=True
        )
        return await utils.answer(message, self.strings["context_text"])