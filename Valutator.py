# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import asyncio
from telethon import events
from telethon.errors.rpcerrorlist import YouBlockedUserError

from .. import loader, utils

class ValutatorMod(loader.Module):
    """Работает с помощью бота @Deltatale_Currency_Converter_Bot"""
    strings = {"name": "Valutator"}

    async def currcmd(self, message):
        """.curr <кол-во> <валюта>
        Конвертирует валюты
        Пример: '.curr 5000 рублей/руб/rub/RUB'
        """
        state = utils.get_args_raw(message)
        chat = "@Deltatale_Currency_Converter_Bot"
        converting_msg = await utils.answer(message, "<emoji document_id=5346192260029489215>💵</emoji> <b>Конвертирую...</b>")
        
        async with message.client.conversation(chat) as conv:
            try:
                response = conv.wait_event(
                    events.NewMessage(incoming=True, from_users=6215875699)
                )
                bot_send_message = await message.client.send_message(chat, format(state))
                bot_response = await response
            except YouBlockedUserError:
                await converting_msg.edit("<b>Разблокируй</b> " + chat)
                return
            await converting_msg.delete()
            await message.respond(bot_response.text)