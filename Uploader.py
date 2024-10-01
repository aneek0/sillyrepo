import io
import random
import imghdr
import requests
from telethon.tl.types import Message

from .. import loader, utils


@loader.tds
class FileUploaderMod(loader.Module):
    """Модуль для загрузки файлов на различные файлообменники"""

    strings = {
        "name": "Uploader",
        "uploading": "🚀 <b>Загрузка...</b>",
        "noargs": "🚫 <b>Файл не указан</b>",
        "err": "🚫 <b>Ошибка загрузки</b>",
        "uploaded": '🎡 <b>Файл <a href="{0}">загружен</a></b>!\n\n<code>{0}</code>',
        "not_an_image": "🚫 <b>Поддерживаются только изображения</b>",
    }

    strings_ru = {
        "uploading": "🚀 <b>Загрузка...</b>",
        "noargs": "🚫 <b>Файл не указан</b>",
        "err": "🚫 <b>Ошибка загрузки</b>",
        "uploaded": '🎡 <b>Файл <a href="{0}">загружен</a></b>!\n\n<code>{0}</code>',
        "not_an_image": "🚫 <b>Поддерживаются только изображения</b>",
        "_cmd_doc_oxo": "Загрузить на 0x0.st",
        "_cmd_doc_x0": "Загрузить на x0.at",
        "_cmd_doc_kappa": "Загрузить на kappa.lol",
        "_cmd_doc_catbox": "Загрузить на Catbox",
    }

    async def get_media(self, message: Message):
        """Получение файла из сообщения"""
        reply = await message.get_reply_message()
        media = None

        if reply and reply.media:
            media = reply
        elif message.media:
            media = message
        elif not reply:
            await utils.answer(message, self.strings("noargs"))
            return False

        if not media:
            file = io.BytesIO(bytes(reply.raw_text, "utf-8"))
            file.name = "file.txt"
        else:
            file = io.BytesIO(await self._client.download_media(media, bytes))
            file.name = (
                media.file.name
                or (
                    "".join(
                        random.choice("abcdefghijklmnopqrstuvwxyz1234567890")
                        for _ in range(16)
                    )
                )
                + media.file.ext
            )

        return file

    async def get_image(self, message: Message):
        """Проверка на изображение и возврат файла"""
        file = await self.get_media(message)
        if not file:
            return False

        if imghdr.what(file) not in ["gif", "png", "jpg", "jpeg", "tiff", "bmp"]:
            await utils.answer(message, self.strings("not_an_image"))
            return False

        return file

    async def oxocmd(self, message: Message):
        """Загрузка на 0x0.st"""
        message = await utils.answer(message, self.strings("uploading"))
        file = await self.get_media(message)
        if not file:
            return

        try:
            oxo = await utils.run_sync(
                requests.post,
                "https://0x0.st",
                files={"file": file},
                data={"secret": True},
            )
        except ConnectionError:
            await utils.answer(message, self.strings("err"))
            return

        url = oxo.text
        await utils.answer(message, self.strings("uploaded").format(url))

    async def kappacmd(self, message: Message):
        """Загрузка на kappa.lol"""
        message = await utils.answer(message, self.strings("uploading"))
        file = await self.get_media(message)
        if not file:
            return

        try:
            kappa = await utils.run_sync(
                requests.post,
                "https://kappa.lol/api/upload",
                files={"file": file},
            )
        except ConnectionError:
            await utils.answer(message, self.strings("err"))
            return

        url = f"https://kappa.lol/{kappa.json()['id']}"
        await utils.answer(message, self.strings("uploaded").format(url))

    async def catboxcmd(self, message: Message):
        """Загрузка на Catbox"""
        message = await utils.answer(message, self.strings("uploading"))
        file = await self.get_media(message)
        if not file:
            return

        try:
            catbox = await utils.run_sync(
                requests.post,
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": file},
            )
        except ConnectionError:
            await utils.answer(message, self.strings("err"))
            return

        url = catbox.text.strip()
        await utils.answer(message, self.strings("uploaded").format(url))
