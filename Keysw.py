# meta developer: @aneek0

from .. import loader, utils

RuKeys = """ёйцукенгшщзхъфывапролджэячсмитьбю.Ё"№;%:?ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭ/ЯЧСМИТЬБЮ,"""
EnKeys = """`qwertyuiop[]asdfghjkl;'zxcvbnm,./~@#$%^&QWERTYUIOP{}ASDFGHJKL:"|ZXCVBNM<>?"""
_switch = str.maketrans(RuKeys + EnKeys, EnKeys + RuKeys)


@loader.tds
class KeyswMod(loader.Module):
    """Реверс раскладки клавиатуры (RU↔EN)"""

    strings = {"name": "Keysw"}

    @loader.unrestricted
    async def keyswcmd(self, message):
        reply = await message.get_reply_message()
        text = utils.get_args_raw(message) or (reply.raw_text if reply else None)
        if not text:
            return await utils.answer(message, "<code>Нет текста</code>")
        text = str.translate(text, _switch)
        if reply and message.sender_id == reply.sender_id:
            await message.delete()
            await reply.edit(text)
        else:
            await message.edit(text)
