# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import io
import re
import aiohttp
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class WebshotMod(loader.Module):
    """Скриншоты сайтов через ScreenshotAPI (https://screenshotapi.to)"""

    BASE_URL = "https://screenshotapi.to/api/v1"
    TIMEOUT = aiohttp.ClientTimeout(total=120)

    strings = {
        "name": "Webshot",
        "no_url": "<emoji document_id=5210952531676504517>❌</emoji> Укажи ссылку! Пример: <code>.webshot example.com</code> или в ответ на сообщение с ссылкой",
        "api_error": "<emoji document_id=5210952531676504517>❌</emoji> Ошибка ScreenshotAPI: <code>{}</code>",
        "request_error": "<emoji document_id=5210952531676504517>❌</emoji> Ошибка запроса: <code>{}</code>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                "API-ключ ScreenshotAPI (https://screenshotapi.to). Без ключа используется бесплатный публичный эндпоинт (8 запросов/мин)",
            ),
        )

    async def webshotcmd(self, message: Message):
        """Скриншот сайта. Флаги: -f вся страница, -dark тёмная тема, -w <px> ширина, -h <px> высота, -t <png|jpeg|webp> формат, -d <ms> задержка"""
        url = utils.get_args_raw(message)
        if not url and message.reply_to_msg_id:
            replied = await message.get_reply_message()
            url = self._extract_url(replied.text) if replied else None
        if not url:
            await utils.answer(message, self.strings["no_url"])
            return

        url = re.sub(r"<.*?>", "", url).strip()
        if not url.startswith("http"):
            url = "https://" + url

        args = utils.get_args(message)
        full = "-f" in args
        dark = "-dark" in args
        ftype = self._flag_value(args, "-t") or "png"
        width = int(self._flag_value(args, "-w") or 1440)
        height = int(self._flag_value(args, "-h") or 900)
        delay = int(self._flag_value(args, "-d") or 0)

        api_key = self.config.get("api_key", None)
        endpoint = f"{self.BASE_URL}/screenshot" if api_key else f"{self.BASE_URL}/public/screenshot"

        params = {
            "url": url,
            "type": ftype,
            "width": min(width, 1920),
            "height": min(height, 10000),
        }
        if full:
            params["fullPage"] = "true"
        if dark:
            params["colorScheme"] = "dark"
        if delay:
            params["delay"] = min(delay, 30000)

        await message.edit("<emoji document_id=5425407515215747798>📸</emoji> Делаю скриншот…")
        try:
            headers = {"x-api-key": api_key} if api_key else {}
            async with aiohttp.ClientSession(timeout=self.TIMEOUT) as session:
                async with session.get(endpoint, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        await utils.answer(message, self.strings["api_error"].format(err[:500]))
                        return
                    data = await resp.read()
        except Exception as e:
            await utils.answer(message, self.strings["request_error"].format(e))
            return

        if ftype == "jpeg":
            ftype = "jpg"
        f = io.BytesIO(data)
        f.name = f"webshot.{ftype}"
        await message.delete()

        flags = " ".join(a for a in args if a.startswith("-"))
        caption = (
            f"<emoji document_id=5425407515215747798>📸</emoji> <code>{url}</code>"
            + (f"\n<b>Флаги:</b> <code>{flags}</code>" if flags else "")
        )
        await self._client.send_file(
            message.chat_id,
            file=f,
            caption=caption,
            force_document=ftype == "pdf",
        )

    def _flag_value(self, args: list, flag: str):
        for i, a in enumerate(args):
            if a == flag and i + 1 < len(args):
                return args[i + 1]
        return None

    def _extract_url(self, text: str) -> str:
        m = re.search(r"(https?://[^\s]+)", text)
        return m.group(0) if m else None
