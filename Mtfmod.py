# meta developer: @aneek0
# scope: hikka_only
# scope: hikka_min 1.2.10

import io

from .. import loader, utils


@loader.tds
class MTFMod(loader.Module):
    """Text ↔ File converter"""

    strings = {"name": "MessageToFile"}

    async def cfcmd(self, message):
        """[filename] — reply to text/file, convert to opposite"""
        reply = await message.get_reply_message()
        if not reply:
            await message.edit("<b>Reply to a message!</b>")
            return

        if reply.file:
            data = await reply.download_media(bytes)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                await message.edit("<b>Not a text file</b>")
                return
            await utils.answer(message, utils.escape_html(text))
        elif reply.message:
            text = bytes(reply.raw_text, "utf-8")
            fname = utils.get_args_raw(message) or f"{message.id}_{reply.id}.txt"
            file = io.BytesIO(text)
            file.name = fname
            await reply.reply(file=file)
            await message.delete()
