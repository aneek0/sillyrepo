# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/
#
# Модуль для получения данных с https://cheburcheck.ru (проверка блокировок РКН,
# IP, подмены DNS и т.д.)

import asyncio

import aiohttp

from .. import loader, utils


async def _fetch(target: str) -> dict:
    """Запрос к API cheburcheck."""
    url = f"https://cheburcheck.ru/api/v1/check?target={target}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
            return await resp.json()


def _fmt_rkn_status(data: dict) -> str:
    blocked = data.get("blocked", False)
    rkn_domain = data.get("rkn_domain")
    if blocked and rkn_domain:
        return "🔴 Заблокирован (в реестре РКН)"
    if rkn_domain:
        return "🟠 Ограничен (частично, по IP/подсетям)"
    return "🟢 Не найден в реестре"


def _fmt_cdn(data: dict) -> str:
    if not data.get("cdn_providers"):
        return "не найдено (риск блокировки по IP)"
    return ", ".join(
        f"{k}: {', '.join(v) if isinstance(v, list) else v}"
        for k, v in data["cdn_providers"].items()
    )


def _fmt(target: str, data: dict) -> str:
    lines = [
        f"🔎 <b>Проверка:</b> <code>{target}</code> (<b>{data.get('target_type') or 'Домен'}</b>)"
    ]

    if data.get("ips"):
        lines.append(f"🌐 <b>IP:</b> <code>{', '.join(data['ips'])}</code>")

    geo = data.get("geo") or {}
    if geo:
        lines.append(
            f"🌍 <b>Гео:</b> {geo.get('location', '?')} · {geo.get('organisation', '?')} · {geo.get('asn', '?')}"
        )

    lines.append(f"📋 <b>Реестр РКН:</b> {_fmt_rkn_status(data)}")

    if data.get("rkn_domain") and data.get("rkn_domain") != data.get("target"):
        lines.append(f"🚫 <b>Заблокированный домен:</b> <code>{data['rkn_domain']}</code>")

    if data.get("blocked_subnets"):
        lines.append(
            f"🧱 <b>Заблокированные подсети:</b> <code>{', '.join(data['blocked_subnets'])}</code>"
        )

    lines.append(f"☁️ <b>CDN:</b> {_fmt_cdn(data)}")

    wl = data.get("whitelist")
    if wl:
        lines.append(
            f"✅ <b>В белом списке:</b> <code>{wl.get('domain')}</code> (рейтинг {wl.get('rank')}, последняя проверка {wl.get('last_ok', '?')[:10]})"
        )

    if data.get("reverse_lookup"):
        lines.append(
            f"🔁 <b>Reverse DNS:</b> <code>{', '.join(data['reverse_lookup'][:4])}</code>"
        )

    lines.append(f"\n🔗 <a href='https://cheburcheck.ru/?target={target}'>Подробнее на сайте</a>")

    return "\n".join(lines)


@loader.tds
class CheburCheckMod(loader.Module):
    """Проверка доменов/IP на блокировки РКН через cheburcheck.ru"""

    strings = {
        "name": "CheburCheck",
        "no_args": "🚫 Укажи домен или IP: <code>.rkn youtube.com</code>",
        "loading": "⏳ Проверяю...",
        "error": "❎ Ошибка при обращении к API. Попробуй позже.",
    }

    async def rkncmd(self, message):
        """.rkn <домен или IP>
        Проверить блокировки РКН, IP, CDN и подмену DNS
        """
        target = utils.get_args_raw(message)
        if not target:
            return await utils.answer(message, self.strings("no_args"))

        target = target.strip().lstrip("h").rstrip("/")
        if target.startswith("ttp"):
            target = "ht" + target

        loading = await utils.answer(message, self.strings("loading"))
        try:
            data = await _fetch(target)
        except Exception:
            await loading.delete()
            return await utils.answer(message, self.strings("error"))

        await loading.delete()
        await utils.answer(message, _fmt(target, data))
