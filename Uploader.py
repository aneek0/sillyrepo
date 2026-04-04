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
        "catbox": ("https://catbox.moe/user/api.php", "fileToUpload", {"reqtype": "fileupload"}),
        "kappa": ("https://kappa.lol/api/upload", "file", None, True),
        "aneeko": ("https://rp.aneeko.online", "file"),
        "rustypaste": ("http://127.0.0.1:8000/", "file", "https://rp.aneeko.online"),
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

    async def upload_file(self, service: str, file, original_name: bool = False):
        if service not in self.SERVICES:
            return f"Неподдерживаемый сервис: {service}"
        config = self.SERVICES[service]
        try:
            # Для rustypaste явно формируем кортеж (filename, file_object)
            if service == "rustypaste":
                fname = file.name if hasattr(file, 'name') and file.name else "file"
                files = {config[1]: (fname, file)}
                data = None
                headers = {}
                if original_name:
                    headers["filename"] = fname
                    headers["overwrite"] = "true"
            else:
                files = {config[1]: file}
                data = config[2] if len(config) > 2 and config[2] else {}
                headers = {}
                if service == "aneeko" and original_name:
                    headers["filename"] = file.name if hasattr(file, 'name') and file.name else "file"
                    headers["overwrite"] = "true"
            
            response = requests.post(config[0], files=files, data=data, headers=headers, timeout=30)
            if response.status_code != 200:
                return f"HTTP {response.status_code}"
            if len(config) > 3 and config[3]:  # kappa
                return f"https://kappa.lol/{response.json()['id']}"
            
            if service == "rustypaste":
                try:
                    rp_url = response.json()["url"]
                    # Заменяем локальный адрес на публичный
                    public_base = config[2] if len(config) > 2 else "https://rp.aneeko.online"
                    local_base = "http://127.0.0.1:8000"
                    return rp_url.replace(local_base, public_base)
                except:
                    return response.text.strip() or None
                    
            return response.text.strip() or None
        except Exception as e:
            return f"Ошибка загрузки: {e}"

    async def handle_upload(self, message: Message, service: str, original_name: bool = False):
        msg = await utils.answer(message, self.strings("uploading"))
        file = await self.get_file(message)
        if not file:
            return
        url = await self.upload_file(service, file, original_name)
        if url and url.startswith("http"):
            await utils.answer(msg, self.strings("uploaded").format(url))
        else:
            await utils.answer(msg, self.strings("error").format(url or "Неизвестная ошибка"))

    async def catboxcmd(self, message: Message):
        """Загрузить файл на catbox.moe"""
        await self.handle_upload(message, "catbox")

    async def kappacmd(self, message: Message):
        """Загрузить файл на kappa.lol"""
        await self.handle_upload(message, "kappa")

    async def aneekocmd(self, message: Message):
        """Загрузить файл на rp.aneeko.online (используйте -n для сохранения имени)"""
        original_name = "-n" in (utils.get_args_raw(message) or "")
        await self.handle_upload(message, "aneeko", original_name)

    async def rupcmd(self, message: Message):
        """Загрузить файл на локальный rustypaste (используйте -n для сохранения имени)"""
        original_name = "-n" in (utils.get_args_raw(message) or "")
        await self.handle_upload(message, "rustypaste", original_name)
