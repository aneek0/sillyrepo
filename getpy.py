# ---------------------------------------------------------------------------------
#  /\_/\  🌐 This module was loaded через https://t.me/hikkamods_bot
# ( o.o )  🔓 Not licensed.
#  > ^ <   ⚠️ Owner of heta.hikariatama.ru doesn't take any responsibilities или intellectual property rights regarding this script
# ---------------------------------------------------------------------------------
# Name: GetPyFilesMod
# Description: Получает имена файлов с расширением .py из указанного репозитория GitHub
# Author: Yahikoro
# Commands:
# .getpy <ссылка на репозиторий> - Возвращает список имён файлов с расширением .py
# ---------------------------------------------------------------------------------

import requests
import re

from .. import loader, utils

@loader.tds
class GetPyFilesMod(loader.Module):
    """Модуль для получения имён файлов с расширением .py из репозитория GitHub"""

    strings = {
        "name": "GetPyFilesMod",
        "invalid_url": "<b>Укажите корректную ссылку на репозиторий GitHub!</b>",
        "no_files_found": "<b>Не найдено ни одного файла с расширением .py.</b>",
        "fetching_files": "<i>Ищу файлы...</i>",
    }

    def init(self):
        self.config = loader.ModuleConfig()

    async def getpycmd(self, message):
        """<ссылка на репозиторий> - Возвращает список имён файлов с расширением .py"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("invalid_url", message))
            return
        
        repo_url = args.rstrip("/")
        api_url = repo_url.replace("github.com", "api.github.com/repos") + "/contents"

        await utils.answer(message, self.strings("fetching_files", message))

        try:
            response = requests.get(api_url)
            response.raise_for_status()

            data = response.json()
            py_files = [
                re.sub(r"\.py$", "", file["name"])
                for file in data
                if file["name"].endswith(".py")
            ]

            if py_files:
                await utils.answer(message, "\n".join(py_files))
            else:
                await utils.answer(message, self.strings("no_files_found", message))

        except requests.RequestException as e:
            await utils.answer(message, f"<b>Произошла ошибка при запросе к GitHub API:</b> <code>{str(e)}</code>")