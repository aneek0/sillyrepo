# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from telethon import events
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

from .. import loader, utils

@loader.tds
class DTSMpd(loader.Module):
    """Модуль для скачивания файлов с возможностью настройки директории."""
    strings = {"name": "Dts"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "DOWNLOAD_DIR", "downloads", "Директория для сохранения скачанных файлов"
        )

    @loader.owner
    async def downcmd(self, message):
        """Скачивает файл, на который был дан ответ."""
        if not message.is_reply:
            await utils.answer(message, "<b>[Downloader]</b> Нет ответа на сообщение с файлом.")
            return

        reply_message = await message.get_reply_message()
        if not reply_message or not (reply_message.media and (isinstance(reply_message.media, (MessageMediaDocument, MessageMediaPhoto)))):
            await utils.answer(message, "<b>[Downloader]</b> В отвеченном сообщении нет файла для скачивания.")
            return

        download_dir = self.config["DOWNLOAD_DIR"]
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        await utils.answer(message, f"<b>[Downloader]</b> Начинаю скачивание в <code>{download_dir}</code>...")
        
        try:
            file_path = await reply_message.download_media(file=download_dir)
            await utils.answer(message, f"<b>[Downloader]</b> Файл успешно скачан и сохранен как <code>{file_path}</code>.")
        except Exception as e:
            await utils.answer(message, f"<b>[Downloader]</b> Произошла ошибка при скачивании: <code>{e}</code>")

