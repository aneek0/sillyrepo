# ---------------------------------------------------------------------------------
# Name: valutator
# Description: Valute converter
# Author: @Azu_nyyyyyyaaaaan
# --------------------------------------------------------------------------------

import asyncio
from telethon import events
from telethon.errors.rpcerrorlist import YouBlockedUserError

from .. import loader, utils


def register(cb):
    cb(ValuesMod())


class ValuesMod(loader.Module):
    """Работает с помощью бота @Deltatale_Currency_Converter_Bot
    """

    strings = {"name": "Valutator"}

    async def currcmd(self, message):
        """.curr <кол-во> <валюта>
        Конвертирует валюты
        Пример: '.curr 5000 рублей/руб/rub/RUB'
        """
        state = utils.get_args_raw(message)
        chat = "@Deltatale_Currency_Converter_Bot"
        async with message.client.conversation(chat) as conv:
            try:
                await message.edit("<emoji document_id=5346192260029489215>💵</emoji> <b>Конвертирую...</b>")
                response = conv.wait_event(
                    events.NewMessage(incoming=True, from_users=6215875699)
                )
                bot_send_message = await message.client.send_message(
                    chat, format(state)
                )
                bot_response = response = await response
            except YouBlockedUserError:
                await message.edit("<b>Разблокируй</b> " + chat)
                return
            await bot_send_message.delete()
            await message.edit(response.text)
            await bot_response.delete()
