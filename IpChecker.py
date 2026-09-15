# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/
#
# Порт плагина "IP Checker" (@akresik) для Materialgram в модуль Hikka/FTG.
# Проверка IP, доменов, VPN-ключей и подсетей через API LatencyLab + WHOIS-агрегаторы.

import asyncio
import ipaddress
import re
import socket

import aiohttp

from .. import loader, utils

LATENCYLAB_BASE = "https://console.latencylab.ru"

WHOIS_APIS = [
    ("api_ip2location", True, "IP2Location", "https://ip2location.com"),
    ("api_ipinfo", False, "IPInfo", "https://ipinfo.io"),
    ("api_ipwhois", False, "IPWhois", "https://ipwhois.io/docs"),
    ("api_ipapi", False, "IP-API", "https://ip-api.com"),
    ("api_freeipapi", False, "FreeIPAPI", "https://freeipapi.com"),
]

OPERATORS = [
    ("op_beeline", "beeline", "Билайн"),
    ("op_megafon", "megafon", "МегаФон"),
    ("op_mts", "mts", "МТС"),
    ("op_t2", "t2", "Теле2"),
    ("op_tmobile", "tmobile", "Т-Мобайл"),
]

def _flag(code: str) -> str:
    code = (code or "").upper()
    if not code:
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)


def _country(code: str) -> str:
    if not code:
        return ""
    return f"{_flag(code)} {code}"


def _is_ip(target: str) -> bool:
    try:
        socket.inet_aton(target)
        parts = target.split(".")
        return len(parts) == 4 and all(
            p.isdigit() and 0 <= int(p) <= 255 for p in parts
        )
    except OSError:
        try:
            socket.inet_pton(socket.AF_INET6, target)
            return True
        except OSError:
            return False


def _is_reserved(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
        return any(
            [
                a.is_private,
                a.is_reserved,
                a.is_loopback,
                a.is_link_local,
                a.is_multicast,
                a.is_unspecified,
            ]
        )
    except ValueError:
        return False


async def _resolve(target: str):
    """Асинхронный DNS-резолв через run_in_executor."""
    if _is_ip(target):
        return target

    def _do():
        a_records, aaaa_records = [], []
        try:
            for item in socket.getaddrinfo(target, None):
                addr = item[4][0]
                try:
                    parsed = ipaddress.ip_address(addr)
                    lst = (
                        a_records
                        if isinstance(parsed, ipaddress.IPv4Address)
                        else aaaa_records
                    )
                    if addr not in lst:
                        lst.append(addr)
                except ValueError:
                    continue
        except socket.gaierror:
            return None
        if not a_records and not aaaa_records:
            return None
        a_records.sort(key=lambda x: tuple(int(o) for o in x.split(".")))
        aaaa_records.sort()
        all_ips = a_records + aaaa_records
        return all_ips[0] if len(all_ips) == 1 else all_ips

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _do)


def _extract_asn(raw: str) -> str:
    raw = (raw or "").strip()
    if raw.upper().startswith("AS"):
        num = raw[2:].split()[0] if raw[2:].split() else ""
        return num if num.isdigit() else ""
    return ""


def _line(label: str, value) -> str:
    if value is None or value == "" or value == "-":
        return ""
    return f"<b>{label}:</b> <code>{value}</code>"


def _fmt_links(ip: str) -> str:
    return (
        "🔗 "
        f"<a href='https://check-host.net/ip-info?host={ip}'>Check-Host</a> | "
        f"<a href='https://bgp.tools/prefix/{ip}'>BGP.tools</a> | "
        f"<a href='https://apps.db.ripe.net/db-web-ui/query?searchtext={ip}'>RIPE</a> | "
        f"<a href='https://www.shodan.io/host/{ip}'>Shodan</a> | "
        f"<a href='https://www.abuseipdb.com/check/{ip}'>AbuseIPDB</a>"
    )


def _op_names(slugs: list) -> str:
    by_slug = {slug: name for _, slug, name in OPERATORS}
    return ", ".join(by_slug.get(s, s) for s in slugs)


def _tcp_label(ch: dict) -> str:
    method = (ch.get("method") or ch.get("ping_method") or "").lower()
    return "TLS" if "tls" in method else "TCP"


@loader.tds
class IpCheckerMod(loader.Module):
    """Проверка IP, доменов, VPN-ключей и подсетей (порт плагина IP Checker от @akresik)"""

    strings = {
        "name": "IpChecker",
        "no_args_wh": "🚫 Укажи IP или домен: <code>.wh 8.8.8.8</code> или <code>.wh google.com</code>",
        "no_args_bs": "🚫 Укажи IP или домен: <code>.bs 77.88.55.88</code> или <code>.bs ya.ru</code>",
        "no_args_vpn": "🚫 Укажи VPN-ключ: <code>.vpn vless://...</code> (<code>ss://</code>, <code>hysteria2://</code>, <code>trojan://</code>)",
        "no_args_sn": "🚫 Укажи подсеть: <code>.sn 1.2.3.0/24</code> (от /23 до /32)",
        "loading": "⏳ Проверяю...",
        "reserved": "🚫 IP-адрес <code>{ip}</code> является зарезервированным",
        "domain_not_found": "🚫 Домена <code>{domain}</code> не существует",
        "multi_ip": (
            "ℹ️ У домена <b>{domain}</b> несколько IP адресов, "
            "скопируй нужный и используй его:\n{ips}"
        ),
        "no_api_key": (
            "🔑 Не указан API-ключ LatencyLab в настройках модуля\n"
            "Получить: <code>.config IpChecker api_key &lt;ключ&gt;</code>\n"
            "Ключ берётся у @Latency_Lab_bot (Профиль → Создать API-ключ)"
        ),
        "invalid_key": "🔑 Ключ, указанный в настройках модуля, является недействительным",
        "no_operators": "🚫 Не выбран ни один оператор в настройках модуля",
        "no_channels": "🚫 Ни один из выбранных операторов недоступен",
        "bad_subnet": "🚫 Укажи подсеть в формате <code>x.x.x.x/xx</code>, например <code>1.2.3.0/24</code> (от /23 до /32)",
        "api_error": "🚫 {}",
        "error": "❎ Ошибка: <i>{}</i>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                lambda: "API-ключ LatencyLab (получить у @Latency_Lab_bot)",
            ),
            loader.ConfigValue(
                "op_beeline",
                True,
                lambda: "Проверять через Билайн",
            ),
            loader.ConfigValue(
                "op_megafon",
                True,
                lambda: "Проверять через МегаФон",
            ),
            loader.ConfigValue(
                "op_mts",
                True,
                lambda: "Проверять через МТС",
            ),
            loader.ConfigValue(
                "op_t2",
                True,
                lambda: "Проверять через Теле2",
            ),
            loader.ConfigValue(
                "op_tmobile",
                True,
                lambda: "Проверять через Т-Мобайл",
            ),
            *[
                loader.ConfigValue(
                    key,
                    default,
                    lambda title=title, url=url: f"Использовать WHOIS-источник {title} ({url})",
                )
                for key, default, title, url in WHOIS_APIS
            ],
        )

    def _ll_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=self._ll_headers(),
        )

    def _ll_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json",
        }

    def _enabled_operators(self) -> list:
        return [
            (slug, name)
            for key, slug, name in OPERATORS
            if bool(self.config[key])
        ]

    async def _get_target_ip(self, message, target: str):
        """Резолвит цель. Возвращает IP или None (при этом сам отвечает в чат)."""
        resolved = await _resolve(target)
        if resolved is None:
            await utils.answer(
                message,
                self.strings("domain_not_found").format(
                    domain=target if len(target) <= 10 else target[:10] + "…"
                ),
            )
            return None
        if isinstance(resolved, list):
            await utils.answer(
                message,
                self.strings("multi_ip").format(
                    domain=target,
                    ips="\n".join(f"<code>{ip}</code>" for ip in resolved),
                ),
            )
            return None
        return resolved

    # ---------------------------------------------------------------- WHOIS

    async def _fetch_ip2location(self, session: aiohttp.ClientSession, ip: str) -> str:
        title, url = "IP2Location", "https://ip2location.com"
        try:
            async with session.get(f"https://api.ip2location.io/?ip={ip}") as resp:
                r = await resp.json()
            if r.get("error"):
                msg = (r.get("error") or {}).get("error_message", "Не найдено")
                return f"<b><a href='{url}'>{title}</a></b>\n🚫 Ошибка: {msg}"
            lines = [
                _line("Страна", _country(r.get("country_code", ""))),
                _line("Город", r.get("city_name", "")),
                _line("Провайдер", r.get("as", "")),
                _line("ASN", r.get("asn", "")),
            ]
        except Exception:
            return f"<b><a href='{url}'>{title}</a></b>\n🚫 Ошибка: сетевая ошибка"
        return f"<b><a href='{url}'>{title}</a></b>\n" + "\n".join(
            l for l in lines if l
        )

    async def _fetch_ipinfo(self, session: aiohttp.ClientSession, ip: str) -> str:
        title, url = "IPInfo", "https://ipinfo.io"
        try:
            async with session.get(f"https://ipinfo.io/{ip}/json") as resp:
                r = await resp.json()
            if r.get("error"):
                msg = (r.get("error") or {}).get("message", "Не найдено")
                return f"<b><a href='{url}'>{title}</a></b>\n🚫 Ошибка: {msg}"
            org_raw = r.get("org", "")
            provider = (
                org_raw.split(" ", 1)[1].strip()
                if org_raw and " " in org_raw
                else org_raw
            )
            lines = [
                _line("Страна", _country(r.get("country", ""))),
                _line("Город", r.get("city", "")),
                _line("Провайдер", provider),
                _line("ASN", _extract_asn(org_raw)),
            ]
        except Exception:
            return f"<b><a href='{url}'>{title}</a></b>\n🚫 Ошибка: сетевая ошибка"
        return f"<b><a href='{url}'>{title}</a></b>\n" + "\n".join(
            l for l in lines if l
        )

    async def _fetch_ipwhois(self, session: aiohttp.ClientSession, ip: str) -> str:
        title, url = "IPWhois", "https://ipwhois.io/docs"
        try:
            async with session.get(f"https://ipwhois.app/json/{ip}") as resp:
                r = await resp.json()
            if not r.get("success", True):
                return (
                    f"<b><a href='{url}'>{title}</a></b>\n"
                    f"🚫 Ошибка: {r.get('message', 'Не найдено')}"
                )
            connection = r.get("connection") or {}
            lines = [
                _line("Страна", _country(r.get("country_code", ""))),
                _line("Город", r.get("city", "")),
                _line("Провайдер", connection.get("isp", "")),
                _line("ASN", connection.get("asn", "")),
            ]
        except Exception:
            return f"<b><a href='{url}'>{title}</a></b>\n🚫 Ошибка: сетевая ошибка"
        return f"<b><a href='{url}'>{title}</a></b>\n" + "\n".join(
            l for l in lines if l
        )

    async def _fetch_ipapi(self, session: aiohttp.ClientSession, ip: str) -> str:
        title, url = "IP-API", "https://ip-api.com"
        try:
            async with session.get(
                f"http://ip-api.com/json/{ip}"
                "?fields=status,message,countryCode,city,isp,as"
            ) as resp:
                r = await resp.json()
            if r.get("status") != "success":
                return (
                    f"<b><a href='{url}'>{title}</a></b>\n"
                    f"🚫 Ошибка: {r.get('message', 'Не найдено')}"
                )
            lines = [
                _line("Страна", _country(r.get("countryCode", ""))),
                _line("Город", r.get("city", "")),
                _line("Провайдер", r.get("isp", "")),
                _line("ASN", _extract_asn(r.get("as", ""))),
            ]
        except Exception:
            return f"<b><a href='{url}'>{title}</a></b>\n🚫 Ошибка: сетевая ошибка"
        return f"<b><a href='{url}'>{title}</a></b>\n" + "\n".join(
            l for l in lines if l
        )

    async def _fetch_freeipapi(self, session: aiohttp.ClientSession, ip: str) -> str:
        title, url = "FreeIPAPI", "https://freeipapi.com"
        try:
            async with session.get(f"https://free.freeipapi.com/api/json/{ip}") as resp:
                r = await resp.json()
            lines = [
                _line("Страна", _country(r.get("countryCode", ""))),
                _line("Город", r.get("cityName", "")),
                _line("Провайдер", r.get("asnOrganization", "")),
                _line("ASN", r.get("asn", "")),
            ]
        except Exception:
            return f"<b><a href='{url}'>{title}</a></b>\n🚫 Ошибка: сетевая ошибка"
        return f"<b><a href='{url}'>{title}</a></b>\n" + "\n".join(
            l for l in lines if l
        )

    _WHOIS_FETCHERS = {
        "api_ip2location": _fetch_ip2location,
        "api_ipinfo": _fetch_ipinfo,
        "api_ipwhois": _fetch_ipwhois,
        "api_ipapi": _fetch_ipapi,
        "api_freeipapi": _fetch_freeipapi,
    }

    async def _get_provider(self, ip: str) -> str:
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(
                    f"https://free.freeipapi.com/api/json/{ip}"
                ) as resp:
                    if resp.status == 200:
                        r = await resp.json()
                        return r.get("asnOrganization") or ""
        except Exception:
            pass
        return ""

    @loader.unrestricted
    async def whcmd(self, message):
        """.wh <IP/домен>
        Информация о цели: страна, город, провайдер, ASN через несколько API
        """
        target = (utils.get_args_raw(message) or "").strip()
        if not target:
            return await utils.answer(message, self.strings("no_args_wh"))

        target = target.split()[0]
        if _is_ip(target) and _is_reserved(target):
            return await utils.answer(
                message, self.strings("reserved").format(ip=target)
            )

        loading = await utils.answer(message, self.strings("loading"))

        if not _is_ip(target):
            resolved = await _resolve(target)
            if resolved is None:
                return await utils.answer(
                    loading,
                    self.strings("domain_not_found").format(
                        domain=target if len(target) <= 10 else target[:10] + "…"
                    ),
                )
            if isinstance(resolved, list):
                return await utils.answer(
                    loading,
                    self.strings("multi_ip").format(
                        domain=target,
                        ips="\n".join(f"<code>{ip}</code>" for ip in resolved),
                    ),
                )
            ip = resolved
            head = (
                f"🎯 <b>Цель:</b> <code>{target}</code>\n"
                f"🌐 <b>IP:</b> <code>{ip}</code>"
            )
        else:
            ip = target
            head = f"🎯 <b>Цель:</b> <code>{target}</code>"

        sections = [head, _fmt_links(ip)]

        fetchers = []
        for key, _default, _title, _url in WHOIS_APIS:
            if bool(self.config[key]):
                fetchers.append(self._WHOIS_FETCHERS[key])

        if fetchers:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            ) as session:
                results = await asyncio.gather(
                    *[fetcher(self, session, ip) for fetcher in fetchers]
                )
            sections.extend(results)

        await utils.answer(loading, "\n".join(sections))

    # ---------------------------------------------------------- LatencyLab

    async def _ll_get_online_operators(self, session):
        """Набор онлайн-операторов или None, если статус узнать не удалось."""
        try:
            async with session.get(
                f"{LATENCYLAB_BASE}/api/lab/operators"
            ) as resp:
                if resp.status == 401:
                    raise PermissionError("401")
                if resp.status == 200:
                    data = (await resp.json()).get("result") or {}
                    if isinstance(data, dict):
                        return {
                            o.get("id")
                            for o in (data.get("operators") or [])
                            if o.get("online")
                        }
                    if isinstance(data, list):
                        return {o.get("slug") for o in data}
        except PermissionError:
            raise
        except Exception:
            pass
        return None

    async def _ll_poll_job(self, session, req_id: str, timeout: int = 120) -> dict:
        for _ in range(timeout):
            await asyncio.sleep(1)
            async with session.get(f"{LATENCYLAB_BASE}/api/lab/job/{req_id}") as resp:
                if resp.status == 401:
                    raise PermissionError("401")
                if resp.status == 404:
                    raise RuntimeError("Задача не найдена на сервере")
                if resp.status != 200:
                    continue
                data = await resp.json()
            status = data.get("status")
            if status == "done":
                return data.get("result") or {}
            if status == "cancelled":
                raise RuntimeError("Скан был отменён")
            if status == "error" or not data.get("ok"):
                raise RuntimeError(
                    f"Ошибка скана: {data.get('error', 'Неизвестная ошибка')}"
                )
        raise RuntimeError("Превышено время ожидания результата")

    async def _ll_start_multiscan(
        self, session, target: str, operators: list = None
    ):
        body = {"text": target, "async": True}
        if operators is not None:
            body["operators"] = operators
        async with session.post(
            f"{LATENCYLAB_BASE}/api/lab/multiscan", json=body
        ) as resp:
            if resp.status == 409:
                rb = await resp.json()
                req_id = rb.get("req_id")
                if req_id:
                    return None, req_id
                raise RuntimeError(
                    f"Уже выполняется другой скан ({rb.get('scan_target', '')})"
                )
            if resp.status == 401:
                raise PermissionError("401")
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
            rb = await resp.json()
            if not rb.get("ok"):
                raise RuntimeError(
                    f"Ошибка запуска: {rb.get('error', 'Неизвестная ошибка')}"
                )
            return (rb["result"], None) if rb.get("result") else (None, rb.get("req_id"))

    @loader.unrestricted
    async def bscmd(self, message):
        """.bs <IP/домен>
        Проверка на белый IP по операторам (Билайн, МегаФон, МТС, Теле2, Т-Мобайл)
        """
        target = (utils.get_args_raw(message) or "").strip()
        if not target:
            return await utils.answer(message, self.strings("no_args_bs"))

        target = target.split()[0]
        api_key = self.config["api_key"]
        if not api_key:
            return await utils.answer(message, self.strings("no_api_key"))

        ops = self._enabled_operators()
        if not ops:
            return await utils.answer(message, self.strings("no_operators"))

        if _is_ip(target) and _is_reserved(target):
            return await utils.answer(
                message, self.strings("reserved").format(ip=target)
            )

        loading = await utils.answer(message, self.strings("loading"))

        ip = await self._get_target_ip(loading, target)
        if not ip:
            return

        try:
            async with self._ll_session() as session:
                provider = await self._get_provider(ip)
                online = await self._ll_get_online_operators(session)
                channels = [
                    slug
                    for slug, _ in ops
                    if online is None or slug in online
                ]
                if not channels:
                    return await utils.answer(
                        loading, self.strings("no_channels")
                    )

                result, req_id = await self._ll_start_multiscan(
                    session, ip, operators=channels
                )
                if req_id:
                    result = await self._ll_poll_job(session, req_id)
        except PermissionError:
            return await utils.answer(loading, self.strings("invalid_key"))
        except Exception as e:
            return await utils.answer(loading, self.strings("error").format(e))

        by_slug = {
            ch.get("operator"): ch for ch in (result.get("results") or [])
        }
        rows = [f"<b>🔎 Проверка на белый IP:</b> <code>{ip}</code>"]
        if provider:
            rows.append(f"<b>🏢 Провайдер:</b> <code>{provider}</code>")
        rows.append("")
        checked = set(result.get("operators") or [])
        for slug, name in ops:
            if slug not in checked:
                continue
            ch = by_slug.get(slug) or {}
            if not ch.get("ok"):
                rows.append(f"<b>{name}:</b> ICMP ❌ | TCP ❌")
                continue
            icmp = "✅" if ch.get("icmp_ok") else "❌"
            tcp = "✅" if ch.get("tcp_ok") else "❌"
            rows.append(
                f"<b>{name}:</b> ICMP {icmp} | {_tcp_label(ch)} {tcp}"
            )

        await utils.answer(loading, "\n".join(rows))

    @loader.unrestricted
    async def bslcmd(self, message):
        """.bsl
        Статистика использования API-лимитов LatencyLab
        """
        api_key = self.config["api_key"]
        if not api_key:
            return await utils.answer(message, self.strings("no_api_key"))

        loading = await utils.answer(message, self.strings("loading"))

        try:
            async with self._ll_session() as session:
                async with session.get(
                    f"{LATENCYLAB_BASE}/api/lab/account/stats"
                ) as resp:
                    if resp.status == 401:
                        raise PermissionError("401")
                    resp.raise_for_status()
                    body = await resp.json()
                if not body.get("ok"):
                    raise RuntimeError(
                        body.get("error", "Неизвестная ошибка")
                    )
                res = body["result"]

                agent_online = False
                ops_online = []
                try:
                    async with session.get(
                        f"{LATENCYLAB_BASE}/api/lab/status"
                    ) as resp:
                        if resp.status == 200:
                            ops_data = (await resp.json()).get("result") or {}
                            agent_online = True
                            if isinstance(ops_data, dict):
                                ops_online = ops_data.get("online", [])
                except Exception:
                    pass
        except PermissionError:
            return await utils.answer(loading, self.strings("invalid_key"))
        except Exception as e:
            return await utils.answer(loading, self.strings("error").format(e))

        window = res.get("window") or {}
        day = res.get("day") or {}
        by_kind = res.get("by_kind") or {}
        window_h = (window.get("window_sec", 86400) or 86400) // 3600

        lines = [
            f"<b>Лимит:</b> {window.get('used', '?')}/{window.get('limit', '?')} за {window_h}ч",
            f"<b>За сегодня:</b> {day.get('total', '?')}",
            f"<b>Всего:</b> {res.get('total', '?')}",
            "",
            f"<b>IP:</b> {by_kind.get('ip', 0)}",
            f"<b>Домен:</b> {by_kind.get('domain', 0)}",
            f"<b>Подсеть:</b> {by_kind.get('subnet', 0)}",
            f"<b>VPN:</b> {by_kind.get('vpn_key', 0)}",
        ]
        if agent_online:
            lines += ["", f"<b>Агент:</b> 🟢 онлайн"]
            if ops_online:
                lines.append(
                    f"<b>Онлайн:</b> {_op_names(ops_online)}"
                )

        await utils.answer(loading, "\n".join(lines))

    @loader.unrestricted
    async def vpncmd(self, message):
        """.vpn <ключ>
        Проверка VPN-ключа (vless://, ss://, hysteria2://, trojan://) по операторам
        """
        uri = (utils.get_args_raw(message) or "").strip()
        if not uri:
            return await utils.answer(message, self.strings("no_args_vpn"))

        api_key = self.config["api_key"]
        if not api_key:
            return await utils.answer(message, self.strings("no_api_key"))
        if not self._enabled_operators():
            return await utils.answer(message, self.strings("no_operators"))

        loading = await utils.answer(message, self.strings("loading"))

        try:
            async with self._ll_session() as session:
                async with session.post(
                    f"{LATENCYLAB_BASE}/api/lab/vpn-key", json={"uri": uri}
                ) as resp:
                    if resp.status == 409:
                        rb = await resp.json()
                        req_id = rb.get("req_id")
                        if not req_id:
                            raise RuntimeError(
                                "Уже выполняется другой скан "
                                f"({rb.get('scan_target', '')})"
                            )
                    else:
                        resp.raise_for_status()
                        rb = await resp.json()
                        if not rb.get("ok"):
                            raise RuntimeError(
                                f"Ошибка: {rb.get('error', 'Неизвестная ошибка')}"
                            )
                        req_id = rb.get("req_id")
                if not req_id:
                    raise RuntimeError("Не удалось получить ID задачи")
                result = await self._ll_poll_job(session, req_id)
        except PermissionError:
            return await utils.answer(loading, self.strings("invalid_key"))
        except Exception as e:
            return await utils.answer(loading, self.strings("error").format(e))

        label = result.get("label", "")
        target = result.get("target", "")
        ip_only = target.split(":")[0] if ":" in target else target
        provider = await self._get_provider(ip_only) if ip_only else ""

        rows = [f"<b>🔑 Проверка VPN-ключа:</b> <code>{label}</code>"]
        if provider:
            rows.append(f"<b>🏢 Провайдер:</b> <code>{provider}</code>")
        if ip_only:
            rows.append(f"<b>🌐 Входной IP:</b> <code>{ip_only}</code>")
        rows.append("")

        by_slug = {
            ch.get("operator"): ch for ch in (result.get("results") or [])
        }
        for slug, name in self._enabled_operators():
            ch = by_slug.get(slug)
            if not ch:
                continue
            if not ch.get("ok"):
                rows.append(f"<b>{name}:</b> недоступен")
                continue
            ms = ch.get("latency_ms")
            rows.append(
                f"<b>{name}:</b> {round(ms) if ms is not None else '—'}ms"
            )

        await utils.answer(loading, "\n".join(rows))

    @loader.unrestricted
    async def sncmd(self, message):
        """.sn <подсеть>
        Скан подсети (/23–/32) по операторам
        """
        target = (utils.get_args_raw(message) or "").strip()
        if not target:
            return await utils.answer(message, self.strings("no_args_sn"))

        parts = target.split()
        target = parts[0]

        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$", target):
            return await utils.answer(message, self.strings("bad_subnet"))
        prefix = int(target.split("/")[1])
        if prefix < 23 or prefix > 32:
            return await utils.answer(message, self.strings("bad_subnet"))

        api_key = self.config["api_key"]
        if not api_key:
            return await utils.answer(message, self.strings("no_api_key"))
        if not self._enabled_operators():
            return await utils.answer(message, self.strings("no_operators"))

        loading = await utils.answer(message, self.strings("loading"))

        try:
            async with self._ll_session() as session:
                result, req_id = await self._ll_start_multiscan(
                    session, target
                )
                if req_id:
                    result = await self._ll_poll_job(session, req_id)
        except PermissionError:
            return await utils.answer(loading, self.strings("invalid_key"))
        except Exception as e:
            return await utils.answer(loading, self.strings("error").format(e))

        norm_target = result.get("target", target)
        first = (result.get("results") or [{}])[0]
        wire_icmp = first.get("icmp_wire", 0)
        wire_tcp = first.get("tcp_wire", 0)

        rows = [f"<b>📡 Проверка подсети:</b> <code>{norm_target}</code>"]
        rows.append(
            f"<b>🔌 Провод:</b> ICMP {wire_icmp} | TCP {wire_tcp}"
        )
        rows.append("")

        by_slug = {
            ch.get("operator"): ch for ch in (result.get("results") or [])
        }
        for slug, name in self._enabled_operators():
            ch = by_slug.get(slug)
            if not ch:
                continue
            if not ch.get("ok"):
                rows.append(f"<b>{name}:</b> ICMP ❌ | TCP ❌")
                continue
            status = ch.get("status_emoji", "")
            rows.append(
                f"<b>{name}:</b> {status} ICMP {ch.get('icmp_alive', 0)}/{wire_icmp}"
                f" | {_tcp_label(ch)} {ch.get('tcp_alive', 0)}/{wire_tcp}"
            )

        await utils.answer(loading, "\n".join(rows))
