# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import subprocess
import traceback
from .. import loader, utils

@loader.tds
class FastfetchMod(loader.Module):
    strings = {"name": "Fastfetch"}

    async def fastfetchcmd(self, message):
        """Запустить команду fastfetch"""
        try:
            result = subprocess.run(["fastfetch"], capture_output=True, text=True)
            output = result.stdout

            if result.returncode != 0:
                await utils.answer(message, f"<b>Ошибка выполнения команды fastfetch:</b>\n{result.stderr}")
                return

            await utils.answer(message, f"<pre>{utils.escape_html(output)}</pre>")
        except Exception:
            await utils.answer(message, f"<b>Ошибка:</b>\n<pre>{traceback.format_exc()}</pre>")