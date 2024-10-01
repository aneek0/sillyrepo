# ---------------------------------------------------------------------------------
#  /\_/\  🌐 This module was loaded через https://t.me/hikkamods_bot
# ( o.o )  🔓 Not licensed.
#  > ^ <   ⚠️ Owner of heta.hikariatama.ru не несет ответственности или прав интеллектуальной собственности на этот скрипт
# ---------------------------------------------------------------------------------
# Name: DaddyResponder
# Description: Изменяет сообщение на "Папочка *исходный текст*" при ответе на сообщения от пользователя с определенным ID
# Author: chatGPT
# ---------------------------------------------------------------------------------

from .. import loader, utils
import logging

TARGET_USER_ID = 677965740

class DaddyResponder(loader.Module):
    """Изменяет сообщение на "Папочка *исходный текст*" при ответе на сообщения от пользователя с определенным ID."""

    strings = {"name": "DaddyResponder"}

    async def client_ready(self, client, db):
        self.client = client

    async def watcher(self, message):
        try:
            if message.is_reply:
                reply_message = await message.get_reply_message()
                if reply_message and reply_message.sender_id == TARGET_USER_ID and message.from_id == (await self.client.get_me()).id:
                    original_text = message.text
                    new_text = f"Папочка {original_text}"
                    await self.client.edit_message(message.chat_id, message.id, new_text)
        except Exception as e:
            logging.error(f"Error in watcher: {str(e)}")
