import io
import requests
import re
import time
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class Web2fileMod(loader.Module):
    """Download content from link and send it as file"""

    strings = {
        "name": "Web2file",
        "no_args": "🚫 <b>Specify link</b>",
        "fetch_error": "🚫 <b>Download error</b>",
        "progress": "📥 <b>Downloading:</b> {0}% at {1}/s",
    }

    strings_ru = {
        "no_args": "🚫 <b>Укажи ссылку</b>",
        "fetch_error": "🚫 <b>Ошибка загрузки</b>",
        "progress": "📥 <b>Загрузка:</b> {0}% со скоростью {1}/с",
        "_cls_doc": "Скачивает содержимое ссылки и отправляет в виде файла",
    }

    async def web2filecmd(self, message: Message):
        """Send link content as file"""
        website = utils.get_args_raw(message)

        if not website:
            if message.reply_to_msg_id:
                replied_msg = await message.get_reply_message()
                website = self.extract_url_from_text(replied_msg.text) if replied_msg else None
        
        if not website:
            await utils.answer(message, self.strings("no_args", message))
            return

        print(f"URL to fetch: {website}")

        website = re.sub(r'<.*?>', '', website)  # Очистка URL от HTML-тегов
        if not website.startswith("http"):
            website = "http://" + website  # Автоматически добавляем http:// если нет префикса

        print(f"Corrected URL to fetch: {website}")

        try:
            # Стартуем скачивание с использованием stream=True
            response = requests.get(website, stream=True)
            if response.status_code != 200:
                await utils.answer(message, f"🚫 <b>Error {response.status_code}: {response.reason}</b>")
                return

            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            start_time = time.time()

            # Логируем размер содержимого
            print(f"Total file size: {total_size} bytes")

            # Буфер для скачивания
            f = io.BytesIO()

            # Переменная для последнего обновления
            last_update_time = time.time()

            # Обновляем текущее сообщение с прогрессом
            await message.edit(self.strings("progress", message).format(0, "0 B/s"))

            # Скачиваем файл по частям
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Вычисляем процент прогресса
                    progress = (downloaded / total_size) * 100

                    # Вычисляем скорость загрузки (в байтах в секунду)
                    elapsed_time = time.time() - start_time
                    speed = downloaded / elapsed_time if elapsed_time > 0 else 0
                    speed_str = self.format_speed(speed)

                    # Обновляем информацию о прогрессе раз в секунду
                    if time.time() - last_update_time >= 1:
                        await message.edit(self.strings("progress", message).format(int(progress), speed_str))
                        last_update_time = time.time()  # Обновляем время последнего обновления

            f.seek(0)  # Возвращаемся в начало файла перед отправкой

            f.name = website.split("/")[-1] or "file"

        except requests.exceptions.RequestException as e:
            print(f"Request exception: {e}")
            await utils.answer(message, f"🚫 <b>Request error: {e}</b>")
            return
        except Exception as e:
            print(f"Unexpected error: {e}")
            await utils.answer(message, f"🚫 <b>Unexpected error: {e}</b>")
            return

        # Добавляем подпись с URL
        caption = f"📥 Downloaded from: <code>{website}</code>"

        # Отправляем файл с подписью через клиентский метод send_file
        await self._client.send_file(message.chat_id, file=f, caption=caption)

        # Удаляем исходное сообщение
        await message.delete()

    def format_speed(self, speed: float) -> str:
        """Форматирует скорость в удобочитаемом виде"""
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        for unit in units:
            if speed < 1024:
                return f"{speed:.2f} {unit}"
            speed /= 1024
        return f"{speed:.2f} TB/s"

    def extract_url_from_text(self, text: str) -> str:
        """Извлекает URL из текста"""
        url_pattern = r'(https?://[^\s]+)'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        return None
        
