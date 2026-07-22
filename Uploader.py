# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import io
import os
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
        'cfg_userhash': '🔑 Catbox userhash',
    }

    SERVICES = {
        "catbox": {"url": "https://catbox.moe/user/api.php", "field": "fileToUpload", "data": {"reqtype": "fileupload"}},
        "litter": {"url": "https://litterbox.catbox.moe/resources/internals/api.php", "field": "fileToUpload", "data": {"reqtype": "fileupload"}},
        "kappa": {"url": "https://kappa.lol/api/upload", "field": "file", "kappa": True},
        "aneeko": {"url": "https://rp.aneeko.online", "field": "file"},
        "rustypaste": {"url": "http://127.0.0.1:8000/", "field": "file", "public_url": "https://rp.aneeko.online"},
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "CATBOX_USERHASH", "",
            lambda m: self.strings("cfg_userhash", m),
        )

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

    async def upload_file(self, service: str, file, original_name: bool = False, litter_time: str = None):
        if service not in self.SERVICES:
            return f"Неподдерживаемый сервис: {service}"
        cfg = self.SERVICES[service]
        try:
            files = {cfg["field"]: file}
            data = dict(cfg.get("data", {})) if not cfg.get("kappa") else None
            headers = {}

            if service == "catbox":
                userhash = self.config.get("CATBOX_USERHASH") or os.getenv("CATBOX_USERHASH")
                if userhash:
                    data["userhash"] = userhash
            if service == "litter":
                data["time"] = litter_time or "1h"
            if service == "rustypaste":
                fname = file.name if hasattr(file, 'name') and file.name else "file"
                files = {cfg["field"]: (fname, file, 'application/octet-stream')}
                data = None
                if original_name:
                    headers["filename"] = fname
                    headers["overwrite"] = "true"
            elif service == "aneeko" and original_name:
                headers["filename"] = file.name if hasattr(file, 'name') and file.name else "file"
                headers["overwrite"] = "true"

            r = requests.post(cfg["url"], files=files, data=data, headers=headers, timeout=30)
            if r.status_code != 200:
                return f"HTTP {r.status_code}"
            if cfg.get("kappa"):
                return f"https://kappa.lol/{r.json()['id']}"
            if service == "rustypaste":
                public = cfg.get("public_url", "https://rp.aneeko.online")
                return r.text.strip().replace("http://127.0.0.1:8000", public) or None
            return r.text.strip() or None
        except Exception as e:
            return f"Ошибка загрузки: {e}"

    async def handle_upload(self, message: Message, service: str, original_name: bool = False, litter_time: str = None):
        msg = await utils.answer(message, self.strings("uploading"))
        file = await self.get_file(message)
        if not file:
            return
        url = await self.upload_file(service, file, original_name, litter_time)
        if url and url.startswith("http"):
            await utils.answer(msg, self.strings("uploaded").format(url))
        else:
            await utils.answer(msg, self.strings("error").format(url or "Неизвестная ошибка"))

    async def catboxcmd(self, message: Message):
        """Загрузить файл на catbox.moe"""
        await self.handle_upload(message, "catbox")

    async def littercmd(self, message: Message):
        """Загрузить файл на litter.catbox.moe (временное хранилище, используйте -t для времени: 1h/12h/24h/72h)"""
        args = utils.get_args_raw(message) or ""
        time_opt = next((t for t in ["72h", "24h", "12h", "1h"] if t in args), "1h")
        await self.handle_upload(message, "litter", litter_time=time_opt)

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
