# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
from io import BytesIO
from base64 import b64encode, b64decode


@loader.tds
class Base64Mod(loader.Module):
    """Кодирование и декодирование base64"""

    strings = {"name": "base64"}

    @loader.owner
    async def b64ecmd(self, message):
        """.b64encode <(text or media) or (reply to text or media)>"""
        reply = await message.get_reply_message()
        mtext = utils.get_args_raw(message)
        if message.media:
            await message.edit("<b>Загрузка файла...</b>")
            data = await message.client.download_file(message, bytes)
        elif mtext:
            data = bytes(mtext, "utf-8")
        elif reply:
            if reply.media:
                await message.edit("<b>Загрузка файла...</b>")
                data = await message.client.download_file(reply, bytes)
            else:
                data = bytes(reply.raw_text, "utf-8")
        else:
            await message.edit("<b>Что нужно закодировать?</b>")
            return

        output = b64encode(data)

        if len(output) > 4000:
            await message.client.send_file(message.to_id, BytesIO(output), reply_to=reply)
            await message.delete()
        else:
            await message.edit(str(output, "utf-8"))

    @loader.owner
    async def b64dcmd(self, message):
        """.b64decode <text or reply to text>"""
        reply = await message.get_reply_message()
        mtext = utils.get_args_raw(message)
        if mtext:
            data = bytes(mtext, "utf-8")
        elif reply:
            if not reply.raw_text:
                await message.edit("<b>Расшифровка файлов невозможна...</b>")
                return
            data = bytes(reply.raw_text, "utf-8")
        else:
            await message.edit("<b>Что нужно декодировать?</b>")
            return
        try:
            output = b64decode(data)
            decoded = str(output, "utf-8")
            await message.edit(decoded)
        except (ValueError, UnicodeDecodeError):
            await message.edit("<b>Ошибка декодирования!</b>")
