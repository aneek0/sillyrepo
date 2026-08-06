# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/
# Scope: Hikka

"""
Скриншоты сайтов через API screenshotapi.to.

Получите API-ключ на https://screenshotapi.to/dashboard
и укажите его в настройках модуля (поле api_key), либо командой:
.modshot sk_live_...
"""

from .. import loader, utils
import io
import logging
import requests

logger = logging.getLogger(__name__)

API_ENDPOINT = "https://screenshotapi.to/api/v1/screenshot"


@loader.tds
class ScreenshotAPIMod(loader.Module):
    """📸 Скриншоты сайтов через screenshotapi.to. Поддерживает формат, полностраничные снимки, тёмный режим, размер окна и ожидание загрузки."""

    strings = {
        "name": "ScreenShotAPI",
        "need_key": (
            "⚠️ <b>API-ключ не установлен.</b>\n"
            "Получите его на <a href='https://screenshotapi.to/dashboard'>screenshotapi.to/dashboard</a> "
            "и введите: <code>.modshot sk_live_...</code>"
        ),
        "no_url": "⚠️ Укажите ссылку: <code>.shot &lt;url&gt; [опции]</code>",
        "waiting": "📸 Фоткаю <code>{short}</code>...",
        "err": "❌ Ошибка: <i>{msg}</i>",
        "done": "✅ <b>Готово</b> — ⏱ {dur} мс · 💎 осталось кредитов: {credits}",
        "key_set": "✅ Ключ API сохранён. Теперь: <code>.shot &lt;url&gt;</code>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                lambda: "API-ключ для screenshotapi.to (dashboard)",
            ),
            loader.ConfigValue(
                "format",
                "png",
                lambda: "Формат по умолчанию: png / jpeg / webp / pdf",
            ),
            loader.ConfigValue(
                "width",
                1440,
                lambda: "Ширина окна по умолчанию",
            ),
            loader.ConfigValue(
                "height",
                900,
                lambda: "Высота окна по умолчанию",
            ),
            loader.ConfigValue(
                "delay",
                200,
                lambda: "Задержка перед снимком (мс) по умолчанию",
            ),
        )

    @loader.sudo
    async def modshotcmd(self, message):
        """[ключ] — установить API-ключ модуля"""
        key = utils.get_args_raw(message)
        if not key:
            await utils.answer(message, self.strings("need_key"))
            return
        self.set("api_key", key.strip())
        await utils.answer(message, self.strings("key_set"))

    @loader.sudo
    @loader.limit("shot")
    async def shotcmd(self, message):
        """.shot <url> [--format=png] [--full] [--dark] [--w=1440] [--h=900] [--delay=200] [--selector=.class] — скриншот сайта"""
        await self._shot(message)

    @staticmethod
    def _parse_opt(arg: str) -> tuple[str, str]:
        """'--key=value' → ('key', 'value'); '--flag' → ('flag', 'true')."""
        tok = arg.lstrip("-")
        if "=" in tok:
            k, _, v = tok.partition("=")
            return k.lower().strip(), v.strip()
        return tok.lower().strip(), "true"

    async def _shot(self, message):
        api_key = self.get("api_key")
        if not api_key:
            await utils.answer(message, self.strings("need_key"))
            return

        tokens = utils.get_args(message)
        if not tokens:
            await utils.answer(message, self.strings("no_url"))
            return

        url = tokens[0]
        opts = {}
        for tok in tokens[1:]:
            k, v = self._parse_opt(tok)
            if k and k != "url":
                opts[k] = v

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        short = url if len(url) < 42 else url[:39] + "..."
        await utils.answer(message, self.strings("waiting").format(short=short))

        fmt = opts.get("format") or self.config["format"]
        if fmt not in ("png", "jpeg", "webp", "pdf"):
            await utils.answer(
                message,
                self.strings("err").format(msg="неизвестный формат: png / jpeg / webp / pdf"),
            )
            return

        def _get_int(name: str, default: int) -> int:
            try:
                return int(opts[name])
            except (KeyError, TypeError, ValueError):
                return int(default)

        params = {
            "url": url,
            "format": fmt,
            "width": _get_int("w", _get_int("width", self.config["width"])),
            "height": _get_int("h", _get_int("height", self.config["height"])),
            "full_page": "true" if "full" in opts else "false",
            "dark_mode": "true" if "dark" in opts else "false",
            "delay": _get_int("delay", self.config["delay"]),
        }
        if "selector" in opts:
            params["wait_for_selector"] = opts["selector"]

        headers = {"x-api-key": api_key}
        try:
            resp = requests.get(API_ENDPOINT, params=params, headers=headers, timeout=120)
        except requests.RequestException as e:
            await utils.answer(message, self.strings("err").format(msg=str(e)))
            return

        if resp.status_code != 200:
            await utils.answer(
                message, self.strings("err").format(msg=self._error_text(resp))
            )
            return

        credits = resp.headers.get("x-credits-remaining", "?")
        dur = resp.headers.get("x-duration-ms", "?")

        file = io.BytesIO(resp.content)
        file.name = f"screenshot.{fmt}"
        file.seek(0)

        reply = message.reply_to_msg_id or message.id
        await message.client.send_file(
            message.chat_id,
            file,
            reply_to=reply,
            caption=self.strings("done").format(dur=dur, credits=credits),
        )
        await message.delete()

    @staticmethod
    def _error_text(resp) -> str:
        try:
            data = resp.json()
            msg = data.get("message") or data.get("error") or "HTTP %s" % resp.status_code
        except Exception:
            msg = resp.text[:200] or "HTTP %s" % resp.status_code
        return str(msg).replace("<", "&lt;").replace(">", "&gt;")