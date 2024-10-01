from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

from .. import loader, utils

class LoliHentai(loader.Module):
    """This module contains commands related to loli hentai."""

    strings = {
        "name": "LoliHentai",
        "loading_photo": "<emoji document_id=5215327832040811010>⏳</emoji> <b>Loading loli hentai, please wait...</b>",
        "error_loading": "<b>Nothing found, unblock @ferganteusbot idiot</b>",
        "search": "<emoji document_id=5328311576736833844>🔴</emoji> Loading loli hentai, please wait..."
    }

    async def lolicmd(self, message):
        """Displays a random loli image or GIF/video."""
        await utils.answer(message, self.strings["loading_photo"])

        async with self.client.conversation("@ferganteusbot") as conv:
            await conv.send_message("/lh")
            response = await conv.get_response()

            if isinstance(response.media, MessageMediaPhoto):
                photo = await response.download_media("loli_hentai")
                try:
                    await self.client.send_file(message.to_id, photo, reply_to=message)
                except ChatSendMediaForbiddenError:
                    await utils.answer(message, self.strings["error_loading"])
            elif isinstance(response.media, MessageMediaDocument):  # Check for video or GIF
                media = await response.download_media("loli_hentai")
                try:
                    await self.client.send_file(message.to_id, media, reply_to=message)
                except ChatSendMediaForbiddenError:
                    await utils.answer(message, self.strings["error_loading"])

@loader.tds
class LoliHentaiMod(loader.Module):
    def __init__(self):
        self.name = LoliHentai.strings["name"]