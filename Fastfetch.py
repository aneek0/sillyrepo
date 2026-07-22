# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import asyncio
from .. import loader, utils

@loader.tds
class FastfetchMod(loader.Module):
    strings = {"name": "Fastfetch"}

    async def fastfetchcmd(self, message):
        try:
            proc = await asyncio.create_subprocess_exec(
                "fastfetch", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            if proc.returncode != 0:
                await utils.answer(message, f"<b>Ошибка:</b>\n{utils.escape_html(stderr.decode())}")
                return
            out = utils.escape_html(stdout.decode()[:4096])
            await utils.answer(message, f"<pre>{out}</pre>")
        except FileNotFoundError:
            await utils.answer(message, "<b>fastfetch не установлен</b>")
        except asyncio.TimeoutError:
            await utils.answer(message, "<b>fastfetch превысил таймаут (15с)</b>")