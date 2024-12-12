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
        match = re.match(r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)", repo_url)
        if not match:
            await utils.answer(message, self.strings("invalid_url", message))
            return

        owner = match.group("owner")
        repo = match.group("repo")
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"

        await utils.answer(message, self.strings("fetching_files", message))

        try:
            py_files = self.fetch_py_files(api_url)
            if py_files:
                await utils.answer(message, "\n".join(py_files))
            else:
                await utils.answer(message, self.strings("no_files_found", message))

        except requests.RequestException as e:
            await utils.answer(message, f"<b>Произошла ошибка при запросе к GitHub API:</b> <code>{str(e)}</code>")

    def fetch_py_files(self, api_url):
        """Рекурсивно получает файлы .py из всех директорий репозитория."""
        py_files = []
        response = requests.get(api_url)
        response.raise_for_status()

        data = response.json()
        for item in data:
            if item["type"] == "file" and item["name"].endswith(".py"):
                py_files.append(re.sub(r"\.py$", "", item["name"]))
            elif item["type"] == "dir":
                py_files.extend(self.fetch_py_files(item["url"]))
        return py_files
