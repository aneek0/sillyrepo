# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/
#
# Модуль для получения данных с https://cheburcheck.ru — проверка блокировок РКН,
# IP, CDN, подмены DNS и региональных провайдеров (TSPU/DPI).

import json

import aiohttp

from .. import loader, utils

API = "https://cheburcheck.ru/api/v1"

VERDICTS = {
    "tspu_block": "🧱 TSPU-блокировка",
    "sni_block": "🚫 SNI-блокировка",
    "dns_spoofing": "🌀 Подмена DNS",
    "whitelist": "✅ Белый список",
    "cdn_block": "☁️ Блокировка CDN",
    "ok": "🟢 Всё ок",
    "uncertain": "❓ Неопределённо",
}


async def _check(target: str) -> dict:
    """Основная проверка (реестр РКН, IP, гео, CDN)."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API}/check",
            params={"target": target},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
            return await resp.json()


async def _probe(check_id: str) -> list:
    """Динамические пробы по регионам/провайдерам через SSE-стрим."""
    results = []
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API}/probe/{check_id}", timeout=aiohttp.ClientTimeout(total=90)
        ) as resp:
            if resp.status != 200:
                return results
            async for raw in resp.content:
                line = raw.decode(errors="ignore").strip()
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                    except (ValueError, TypeError):
                        continue
                    if isinstance(data, dict) and "probe_id" in data:
                        results.append(data)
    return results


def _verdicts_of_probe(probe: dict) -> str:
    vs = probe.get("verdicts") or []
    return " + ".join(VERDICTS.get(v, v) for v in vs) or "—"


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
            f"✅ <b>В белом списке:</b> <code>{wl.get('domain')}</code> (рейтинг {wl.get('rank')})"
        )

    if data.get("reverse_lookup"):
        lines.append(
            f"🔁 <b>Reverse DNS:</b> <code>{', '.join(data['reverse_lookup'][:4])}</code>"
        )

    lines.append(f"\n🔗 <a href='https://cheburcheck.ru/?target={target}'>Подробнее на сайте</a>")

    return "\n".join(lines)


def _fmt_probes(probes: list) -> str:
    if not probes:
        return ""
    lines = ["", "📡 <b>Проверка по регионам:</b>"]
    for p in sorted(probes, key=lambda x: x.get("probe_id", "")):
        lines.append(
            f"• <b>{p.get('region', '?')}</b> · {p.get('provider', '?')} ({p.get('asn', '?')}): {_verdicts_of_probe(p)}"
        )
    return "\n".join(lines)


@loader.tds
class CheburCheckMod(loader.Module):
    """Проверка доменов/IP на блокировки РКН через cheburcheck.ru"""

    strings = {
        "name": "CheburCheck",
        "no_args": "🚫 Укажи домен или IP: <code>.rkn youtube.com</code>",
        "loading": "⏳ Проверяю...",
        "probing": "📡 Запускаю региональные пробы...",
        "error": "❎ Ошибка при обращении к API. Попробуй позже.",
    }

    async def _get_target(self, message):
        target = utils.get_args_raw(message)
        if not target:
            await utils.answer(message, self.strings("no_args"))
            return None
        return target.strip().rstrip("/")

    @loader.unrestricted
    async def rkncmd(self, message):
        """.rkn <домен или IP>
        Проверить блокировки РКН, IP, CDN
        """
        target = await self._get_target(message)
        if not target:
            return

        loading = await utils.answer(message, self.strings("loading"))
        try:
            data = await _check(target)
        except Exception:
            return await utils.answer(loading, self.strings("error"))

        await utils.answer(loading, _fmt(target, data))

    @loader.unrestricted
    async def rknpcmd(self, message):
        """.rknp <домен или IP>
        Полная проверка: РКН + региональные пробы (TSPU/SNI/подмена DNS)
        """
        target = await self._get_target(message)
        if not target:
            return

        loading = await utils.answer(message, self.strings("loading"))
        try:
            data = await _check(target)
        except Exception:
            return await utils.answer(loading, self.strings("error"))

        await loading.edit(self.strings("probing"))
        try:
            probes = await _probe(data["id"])
        except Exception:
            probes = []

        await utils.answer(loading, _fmt(target, data) + _fmt_probes(probes))
