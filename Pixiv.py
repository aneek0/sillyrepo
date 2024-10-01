import os
import requests
from bs4 import BeautifulSoup
from .. import loader, utils

class PixivDownloaderMod(loader.Module):
    """Модуль для скачивания изображений с Pixiv и отправки в чат"""
    strings = {"name": "PixivDownloader"}

    async def client_ready(self, client, db):
        self.client = client

    @loader.sudo
    async def pixivcmd(self, message):
        """Скачать и отправить изображение с Pixiv"""
        args = utils.get_args_raw(message)
        if not args:
            await message.reply("Укажите ID изображения Pixiv.")
            return

        image_id = args.strip()
        await message.reply("Ищу изображения...")

        search_url = f"https://www.pixiv.net/en/artworks/{image_id}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, как Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            response = requests.get(search_url, headers=headers)
            if response.status_code != 200:
                await message.reply(f"Не удалось получить данные с Pixiv. Статус код: {response.status_code}")
                return

            soup = BeautifulSoup(response.content, 'html.parser')
            image_meta = soup.find("meta", {"property": "og:image"})

            if not image_meta:
                await message.reply("Не удалось найти изображение.")
                return

            image_url = image_meta["content"]
            image_response = requests.get(image_url, headers=headers)
            if image_response.status_code != 200:
                await message.reply(f"Не удалось скачать изображение. Статус код: {image_response.status_code}")
                return

            image_path = os.path.join("downloads", "pixiv", f"{image_id}.jpg")
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            with open(image_path, "wb") as f:
                f.write(image_response.content)

            await self.client.send_file(message.to_id, image_path, caption=f"Изображение с Pixiv: {image_id}")

        except Exception as e:
            await message.reply(f"Произошла ошибка: {str(e)}")

# Регистрация модуля
def register(cb):
    cb(PixivDownloaderMod())
    
