# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils

class TranslitMod(loader.Module):
    """Переводит раскладку клавиатуры"""
    strings = {"name": "TranslitMod"}

    @loader.command()
    async def trccmd(self, message):
        """Переводит раскладку (ответ на сообщение)"""
        reply = await message.get_reply_message()
        if not reply or not reply.text:
            return await utils.answer(message, "<i>❌ Ответьте на сообщение</i>")
        
        text = reply.text
        ru_keys = "йцукенгшщзхъфывапролджэячсмитьбю.Ё\"№;%:?ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭ/ЯЧСМИТЬБЮ,"
        en_keys = "qwertyuiop[]asdfghjkl;'zxcvbnm,./~@#$%^&QWERTYUIOP{}ASDFGHJKL:\"|ZXCVBNM<>?"
        
        change = str.maketrans(ru_keys + en_keys, en_keys + ru_keys)
        result = str.translate(text, change)
        
        await utils.answer(message, f"<code>{result}</code>")
