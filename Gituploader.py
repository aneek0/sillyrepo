# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import base64
import json
import subprocess
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO
from requests.exceptions import ChunkedEncodingError, MissingSchema

from .. import loader, utils

@loader.tds
class GitUploader(loader.Module):
    """Загружает файлы на репозиторий GitHub"""

    strings = {
        "name": "GitUploader",
        "reply_to_file": "<b>Ответьте на файл</b>",
        "connection_error": "<i>Ошибка соединения</i>",
        "repo_error": "<i>Ошибка репозитория</i>",
        "token_error": "<i>Ошибка токена</i>",
        "exist_422": (
            "<b>Не удалось загрузить файл. Возможная причина: файл с таким названием"
            " уже существует в репозитории. Файл будет перезаписан.</b>"
        ),
        "cfg_token": "Токен GitHub",
        "token_not_found": "Токен не найден",
        "username_not_found": "Имя пользователя GitHub не указано",
        "repo_not_found": "Репозиторий не указан",
        "cfg_gh_user": "Имя пользователя на GitHub",
        "cfg_gh_repo": "Репозиторий, куда нужно загружать файлы",
        "specify_filename": "<b>Укажите имя файла</b>",
        "file_not_found": "<b>Файл не найден</b>",
        "file_deleted": "Файл <code>{}</code> удалён",
        "delete_error": "<i>Ошибка удаления файла</i>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "GH_TOKEN",
            "TOKEN",
            lambda m: self.strings("cfg_token", m),
            "GH_USERNAME",
            "USERNAME",
            lambda m: self.strings("cfg_gh_user", m),
            "GH_REPO",
            "REPOSITORY",
            lambda m: self.strings("cfg_gh_repo", m),
        )

    @loader.owner
    async def gitaddcmd(self, message):
        if self.config["GH_TOKEN"] == "TOKEN":
            await utils.answer(message, self.strings("token_not_found", message))
            return
        if self.config["GH_USERNAME"] == "USERNAME":
            await utils.answer(message, self.strings("username_not_found", message))
            return
        if self.config["GH_REPO"] == "REPOSITORY":
            await utils.answer(message, self.strings("repo_not_found", message))
            return

        reply = await message.get_reply_message()
        if not reply or not reply.media:
            await utils.answer(message, self.strings("reply_to_file", message))
            return

        try:
            file = await message.client.download_file(reply.media)

            if hasattr(reply.media, "document"):
                attributes = reply.media.document.attributes
                fname = next((attr.file_name for attr in attributes if hasattr(attr, 'file_name')), None)
                if not fname:
                    fname = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}{self._get_extension(reply.media.document.mime_type)}"
            elif reply.media.photo:
                fname = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                file = self._convert_webp_to_png(file)
            elif reply.media.sticker:
                if reply.media.sticker.is_animated:
                    fname = f"sticker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                    file = self._convert_webm_to_mp4(file)
                else:
                    fname = f"sticker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    file = self._convert_webp_to_png(file)
            elif reply.media.video:
                fname = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            elif reply.media.audio:
                fname = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            else:
                fname = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat"

            # Кодируем файл в base64
            encoded_string = base64.b64encode(file).decode("utf-8")
            TOKEN = self.config["GH_TOKEN"]
            USERNAME = self.config["GH_USERNAME"]
            REPO = self.config["GH_REPO"]
            url = f"https://api.github.com/repos/{USERNAME}/{REPO}/contents/{fname}"
            head = {
                "Authorization": f"token {TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            git_data = json.dumps({
                "message": "Upload file",
                "content": encoded_string
            })

            # Проверка на существование файла и получение SHA для обновления
            r_get = requests.get(url, headers=head)
            if r_get.status_code == 200:
                sha = r_get.json()["sha"]
                git_data = json.dumps({
                    "message": "Update file",
                    "content": encoded_string,
                    "sha": sha
                })

            r = requests.put(url, headers=head, data=git_data)
            if r.status_code == 201 or r.status_code == 200:
                uploaded_to = f"https://github.com/{USERNAME}/{REPO}/blob/main/{fname}"
                uploaded_to_raw = r.json()["content"]["download_url"]
                await utils.answer(
                    message,
                    (
                        f"Файл <code>{fname}</code> успешно загружен на репозиторий!"
                        f"\n\nСсылка на файл:\n<code>{uploaded_to}</code>\n"
                        f"Прямая ссылка:\n<code>{uploaded_to_raw}</code>"
                    ),
                )
            elif r.status_code == 422:
                await utils.answer(message, self.strings("exist_422", message))
            else:
                json_resp = r.json()
                git_resp = json_resp["message"]
                await utils.answer(
                    message,
                    (
                        "Произошла неизвестная ошибка! Ответ сервера:\n"
                        f"<code>{git_resp}</code>"
                    ),
                )
        except requests.ConnectionError:
            await utils.answer(message, self.strings("connection_error", message))
        except MissingSchema:
            await utils.answer(message, self.strings("repo_error", message))
        except ChunkedEncodingError:
            await utils.answer(message, self.strings("token_error", message))

    @loader.owner
    async def gitlscmd(self, message):
        if self.config["GH_TOKEN"] == "TOKEN":
            await utils.answer(message, self.strings("token_not_found", message))
            return
        if self.config["GH_USERNAME"] == "USERNAME":
            await utils.answer(message, self.strings("username_not_found", message))
            return
        if self.config["GH_REPO"] == "REPOSITORY":
            await utils.answer(message, self.strings("repo_not_found", message))
            return

        USERNAME = self.config["GH_USERNAME"]
        REPO = self.config["GH_REPO"]
        url = f"https://api.github.com/repos/{USERNAME}/{REPO}/contents/"
        head = {
            "Authorization": f"token {self.config['GH_TOKEN']}",
            "Accept": "application/vnd.github.v3+json",
        }
        try:
            r = requests.get(url, headers=head)
            if r.status_code == 200:
                files = r.json()
                lines = [f"<code>{f['name']}</code>" for f in files]
                await utils.answer(
                    message, "Файлы в репозитории:\n" + "\n".join(lines)
                )
            else:
                await utils.answer(message, self.strings("repo_error", message))
        except requests.ConnectionError:
            await utils.answer(message, self.strings("connection_error", message))

    @loader.owner
    async def gitrmcmd(self, message):
        if self.config["GH_TOKEN"] == "TOKEN":
            await utils.answer(message, self.strings("token_not_found", message))
            return
        if self.config["GH_USERNAME"] == "USERNAME":
            await utils.answer(message, self.strings("username_not_found", message))
            return
        if self.config["GH_REPO"] == "REPOSITORY":
            await utils.answer(message, self.strings("repo_not_found", message))
            return

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("specify_filename", message))
            return

        USERNAME = self.config["GH_USERNAME"]
        REPO = self.config["GH_REPO"]
        url = f"https://api.github.com/repos/{USERNAME}/{REPO}/contents/{args}"
        head = {
            "Authorization": f"token {self.config['GH_TOKEN']}",
            "Accept": "application/vnd.github.v3+json",
        }
        try:
            r_get = requests.get(url, headers=head)
            if r_get.status_code != 200:
                await utils.answer(message, self.strings("file_not_found", message))
                return
            sha = r_get.json()["sha"]
            r = requests.delete(url, headers=head, json={"message": "Delete file", "sha": sha})
            if r.status_code in (200, 204):
                await utils.answer(
                    message, self.strings("file_deleted", message).format(args)
                )
            else:
                await utils.answer(message, self.strings("delete_error", message))
        except requests.ConnectionError:
            await utils.answer(message, self.strings("connection_error", message))

    def _get_extension(self, mime_type):
        """Определяет расширение файла по MIME-типу."""
        mime_types = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "video/mp4": ".mp4",
            "audio/mpeg": ".mp3",
            "application/pdf": ".pdf",
            "application/zip": ".zip",
        }
        return mime_types.get(mime_type, ".dat")

    def _convert_webp_to_png(self, file_content):
        """Конвертирует WEBP изображение в PNG."""
        image = Image.open(BytesIO(file_content))
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return buffered.getvalue()

    def _convert_webm_to_mp4(self, file_content):
        proc = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-f", "mp4", "pipe:1"],
            input=file_content, capture_output=True, check=True
        )
        return proc.stdout