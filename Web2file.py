# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import io
import requests
import re
import time
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class Web2fileMod(loader.Module):
    strings = {
        "name": "Web2file",
        "no_args": "🚫 <b>Specify link</b>",
        "fetch_error": "🚫 <b>Download error</b>",
        "progress_download": "📥 <b>Downloading:</b> {0}% at {1}/s",
        "progress_upload": "📤 <b>Uploading:</b> {0}% at {1}/s",
    }

    strings_ru = {
        "no_args": "🚫 <b>Укажи ссылку</b>",
        "fetch_error": "🚫 <b>Ошибка загрузки</b>",
        "progress_download": "📥 <b>Загрузка:</b> {0}% со скоростью {1}/с",
        "progress_upload": "📤 <b>Отправка:</b> {0}% со скоростью {1}/с",
        "_cls_doc": "Скачивает содержимое ссылки и отправляет в виде файла",
    }

    async def web2filecmd(self, message: Message):
        website = utils.get_args_raw(message)

        if not website:
            if message.reply_to_msg_id:
                replied_msg = await message.get_reply_message()
                website = self.extract_url_from_text(replied_msg.text) if replied_msg else None
        
        if not website:
            await utils.answer(message, self.strings("no_args", message))
            return

        website = re.sub(r'<.*?>', '', website)
        if not website.startswith("http"):
            website = "http://" + website

        # Delete the original message
        await message.delete()

        # Create new message for progress
        progress_message = await self._client.send_message(
            message.chat_id,
            self.strings("progress_download", message).format(0, "0 B/s")
        )

        try:
            response = requests.get(website, stream=True)
            if response.status_code != 200:
                await utils.answer(progress_message, f"🚫 <b>Error {response.status_code}: {response.reason}</b>")
                return

            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            start_time = time.time()

            f = io.BytesIO()

            last_update_time = time.time()
            last_progress = 0

            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    progress = (downloaded / total_size) * 100

                    elapsed_time = time.time() - start_time
                    speed = downloaded / elapsed_time if elapsed_time > 0 else 0
                    speed_str = self.format_speed(speed)

                    if time.time() - last_update_time >= 1 and int(progress) != last_progress:
                        await progress_message.edit(self.strings("progress_download", message).format(int(progress), speed_str))
                        last_update_time = time.time()
                        last_progress = int(progress)

            f.seek(0)

            f.name = website.split("/")[-1] or "file"

        except requests.exceptions.RequestException as e:
            await utils.answer(progress_message, f"🚫 <b>Request error: {e}</b>")
            return
        except Exception as e:
            await utils.answer(progress_message, f"🚫 <b>Unexpected error: {e}</b>")
            return

        caption = f"📥 Downloaded from: <code>{website}</code>"

        self._upload_start_time = time.time()
        await self._client.send_file(
            message.chat_id,
            file=f,
            caption=caption,
            progress_callback=lambda current, total: self._update_progress_upload(current, total, progress_message),
        )

        await progress_message.delete()

    async def _update_progress_upload(self, current: int, total: int, message: Message):
        progress = (current / total) * 100
        speed = current / (time.time() - self._upload_start_time) if hasattr(self, "_upload_start_time") else 0
        speed_str = self.format_speed(speed)

        if int(progress) != getattr(self, "_last_upload_progress", 0):
            await message.edit(self.strings("progress_upload", message).format(int(progress), speed_str))
            self._last_upload_progress = int(progress)

    def format_speed(self, speed: float) -> str:
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        for unit in units:
            if speed < 1024:
                return f"{speed:.2f} {unit}"
            speed /= 1024
        return f"{speed:.2f} TB/s"

    def extract_url_from_text(self, text: str) -> str:
        url_pattern = r'(https?://[^\s]+)'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        return None