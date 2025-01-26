# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import io
import requests
from telethon.tl.types import Message
from .. import loader, utils

@loader.tds
class UploaderMod(loader.Module):
    """Модуль для загрузки файлов на файлообменники"""

    strings = {
        'name': 'Uploader',
        'uploading': "🚀 <b>Загрузка...</b>',
        'no_file': '🚫 <b>Файл не найден.</b>',
        'uploaded': '🎡 <b>Файл <a href="{0}">загружен</a></b>!\n\n<code>{0}</code>',
        'error': '🚫 <b>Ошибка загрузки:</b> <code>{0}</code>',
    }

    async def get_file(self, message: Message):
        """Получить файл из сообщения"""
        reply = await message.get_reply_message()
        if reply and reply.media:
            file = io.BytesIO()
            await message.client.download_media(reply, file)
            file.seek(0)
            file.name = reply.file.name or "file"
            return file
        elif message.media:
            file = io.BytesIO()
            await message.client.download_media(message, file)
            file.seek(0)
            file.name = message.file.name or "file"
            return file
        else:
            await utils.answer(message, self.strings("no_file"))
            return None

    async def upload_file(self, service: str, file):
        """Загрузить файл на указанный сервис"""
        try:
            if service == "envs":
                response = requests.post("https://envs.sh", files={"file": file})
                return response.text.strip() if response.status_code == 200 else None
            elif service == "catbox":
                response = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": file},
                )
                return response.text.strip() if response.status_code == 200 else None
            elif service == "oxo":
                response = requests.post("https://0x0.st", files={"file": file})
                return response.text.strip() if response.status_code == 200 else None
            elif service == "kappa":
                response = requests.post("https://kappa.lol/api/upload", files={"file": file})
                return f"https://kappa.lol/{response.json()['id']}" if response.status_code == 200 else None
        except Exception as e:
            return str(e)

    async def handle_upload(self, message: Message, service: str):
        """Обработка загрузки файла и вывод результата"""
        await utils.answer(message, self.strings("uploading"))
        file = await self.get_file(message)
        if not file:
            return

        url = await self.upload_file(service, file)
        if url and not url.startswith("http"):
            await utils.answer(message, self.strings("error").format(url))
        elif url:
            await utils.answer(message, self.strings("uploaded").format(url))
        else:
            await utils.answer(message, self.strings("error").format("Неизвестная ошибка"))

    async def envscmd(self, message: Message):
        """Загрузить файл на envs.sh"""
        await self.handle_upload(message, "envs")

    async def catboxcmd(self, message: Message):
        """Загрузить файл на catbox.moe"""
        await self.handle_upload(message, "catbox")

    async def oxocmd(self, message: Message):
        """Загрузить файл на 0x0.st"""
        await self.handle_upload(message, "oxo")

    async def kappacmd(self, message: Message):
        """Загрузить файл на kappa.lol"""
        await self.handle_upload(message, "kappa")
