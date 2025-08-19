# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import asyncio
from telethon import events
from telethon.errors.rpcerrorlist import YouBlockedUserError

from .. import loader, utils

class ValutatorMod(loader.Module):
    """Работает с помощью бота @aneekocurrency_bot"""
    strings = {"name": "Valutator"}

    async def currcmd(self, message):
        """.curr <кол-во> <валюта>
        Конвертирует валюты
        Пример: '.curr 5000 рублей/руб/rub/RUB'
        """
        state = utils.get_args_raw(message)
        chat = "@aneekocurrency_bot"
        
        # Редактируем исходное сообщение, чтобы показать, что мы работаем
        await utils.answer(message, "<emoji document_id=5346192260029489215>💵</emoji> <b>Конвертирую...</b>")
        
        async with message.client.conversation(chat) as conv:
            try:
                # Отправляем запрос боту и ждём ответа
                # Используем from_users=chat для поиска по имени пользователя
                response = conv.wait_event(
                    events.NewMessage(incoming=True, from_users=chat)
                )
                bot_send_message = await message.client.send_message(chat, format(state))
                bot_response = await response
                
            except YouBlockedUserError:
                # Если пользователь заблокировал бота
                await message.edit("<b>Разблокируй</b> " + chat)
                return

            # После получения ответа от бота, редактируем исходное сообщение
            # с результатом
            await message.edit(bot_response.text)