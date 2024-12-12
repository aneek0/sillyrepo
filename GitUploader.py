import base64
import json
import logging
import os
import subprocess
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO
from requests.exceptions import ChunkedEncodingError, MissingSchema

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class GitUploader(loader.Module):
    """Загружает файлы на репозиторий GitHub"""

    strings = {
        "name": "GitUploader",
        "reply_to_file": "<b>Ответьте на файл</b>",
        "error_file": "Формат не поддерживается",
        "connection_error": "<i>Ошибка соединения</i>",
        "repo_error": "<i>Ошибка репозитория</i>",
        "token_error": "<i>Ошибка токена</i>",
        "exist_422": (
            "<b>Не удалось загрузить файл. Возможная причина: файл с таким названием"
            " уже существует в репозитории.</b>"
        ),
        "cfg_token": "Токен GitHub",
        "token_not_found": "Токен не найден",
        "username_not_found": "Имя пользователя GitHub не указано",
        "repo_not_found": "Репозиторий не указан",
        "cfg_gh_user": "Имя пользователя на GitHub",
        "cfg_gh_repo": "Репозиторий, куда нужно загружать файлы",
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

    async def client_ready(self, client, db):
        self.client = client

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
            # Определение имени файла и расширения
            fname = None
            extension = None
            file = await message.client.download_file(reply.media)

            if hasattr(reply.media, "document"):
                attributes = reply.media.document.attributes
                fname = next((attr.file_name for attr in attributes if hasattr(attr, 'file_name')), None)
                if fname:
                    extension = os.path.splitext(fname)[1]
                else:
                    extension = self._get_extension(reply.media.document.mime_type)
                    fname = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
            elif reply.media.photo:
                extension = ".png"
                fname = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                file = self._convert_image_to_png(file)
            elif reply.media.sticker:
                if reply.media.sticker.is_animated:
                    extension = ".mp4"
                    fname = f"sticker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                    file = self._convert_webm_to_mp4(file)
                else:
                    extension = ".png"
                    fname = f"sticker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    file = self._convert_webp_to_png(file)
            elif reply.media.video:
                extension = ".mp4"
                fname = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            elif reply.media.audio:
                extension = ".mp3"
                fname = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            else:
                extension = ".dat"
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
            r = requests.put(url, headers=head, data=git_data)
            if r.status_code == 201:
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

    def _convert_image_to_png(self, file_content):
        """Конвертирует изображение в формат PNG."""
        image = Image.open(BytesIO(file_content))
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return buffered.getvalue()

    def _convert_webp_to_png(self, file_content):
        """Конвертирует WEBP изображение в PNG."""
        image = Image.open(BytesIO(file_content))
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return buffered.getvalue()

    def _convert_webm_to_mp4(self, file_content):
        """Конвертирует WEBM видео в MP4 с использованием ffmpeg."""
        input_file = "input.webm"
        output_file = "output.mp4"

        with open(input_file, "wb") as f_in:
            f_in.write(file_content)

        subprocess.run(["ffmpeg", "-i", input_file, output_file], check=True)

        with open(output_file, "rb") as f_out:
            converted_file = f_out.read()

        os.remove(input_file)
        os.remove(output_file)

        return converted_file
