# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import io
import requests
from telethon.tl.types import Message
from .. import loader, utils

@loader.tds
class UploaderMod(loader.Module):
    strings = {
        'name': 'Uploader',
        'uploading': '🚀 <b>Загрузка...</b>',
        'no_file': '🚫 <b>Файл не найден.</b>',
        'uploaded': '🎡 <b>Файл <a href="{0}">загружен</a></b>!\n\n<code>{0}</code>',
        'error': '🚫 <b>Ошибка загрузки:</b> <code>{0}</code>',
    }

    SERVICES = {
        "envs": ("https://envs.sh", "file"),
        "catbox": ("https://catbox.moe/user/api.php", "fileToUpload", {"reqtype": "fileupload"}),
        "oxo": ("https://0x0.st", "file"),
        "kappa": ("https://kappa.lol/api/upload", "file", None, True),
        "aneeko": ("https://rp.aneeko.online", "file"),
    }

    async def get_file(self, message: Message):
        reply = await message.get_reply_message()
        msg = reply if reply and reply.media else message
        if not msg or not msg.media:
            await utils.answer(message, self.strings("no_file"))
            return None
        file = io.BytesIO()
        await message.client.download_media(msg, file)
        file.seek(0)
        file.name = getattr(msg.file, 'name', None) or "file"
        return file

    async def upload_file(self, service: str, file):
        if service not in self.SERVICES:
            return f"Неподдерживаемый сервис: {service}"
        config = self.SERVICES[service]
        try:
            files = {config[1]: file}
            data = config[2] if len(config) > 2 and config[2] else {}
            response = requests.post(config[0], files=files, data=data, timeout=30)
            if response.status_code != 200:
                return f"HTTP {response.status_code}"
            if len(config) > 3 and config[3]:  # kappa
                return f"https://kappa.lol/{response.json()['id']}"
            return response.text.strip() or None
        except:
            return "Ошибка загрузки"

    async def handle_upload(self, message: Message, service: str):
        msg = await utils.answer(message, self.strings("uploading"))
        file = await self.get_file(message)
        if not file:
            return
        url = await self.upload_file(service, file)
        if url and url.startswith("http"):
            await utils.answer(msg, self.strings("uploaded").format(url))
        else:
            await utils.answer(msg, self.strings("error").format(url or "Неизвестная ошибка"))

    async def envscmd(self, message: Message):
        """Загрузить файл на envs.sh"""
        await self.handle_upload(message, "envs")

    async def catboxcmd(self, message: Message):
        """Загрузить файл на catbox.moe"""
        await self.handle_upload(message, "catbox")

    async def oxocmd(self, message: Message):
        """Загрузить файл на oxo.st"""
        await self.handle_upload(message, "oxo")

    async def kappacmd(self, message: Message):
        """Загрузить файл на kappa.lol"""
        await self.handle_upload(message, "kappa")

    async def aneekocmd(self, message: Message):
        """Загрузить файл на rp.aneeko.online"""
        await self.handle_upload(message, "aneeko")