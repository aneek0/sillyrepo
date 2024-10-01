# ---------------------------------------------------------------------------------
# Name: Yandere
# Description: Отсылает рандомное фото с Yande.re
# Author: Dolbaeb228
# Commands:
# .yandere
# ---------------------------------------------------------------------------------

import random
import requests
from .. import loader, utils

@loader.tds
class YandereMod(loader.Module):
    """Модуль для отправки случайного фото с yande.re"""
    strings = {"name": "yandere",
               "description": "КАК ЖЕ ЭТА ХУЙНЯ МЕНЯ ЗАЕБАЛА СПАСИТЕ"}

    async def client_ready(self, client, db):
        self.client = client

    async def yanderecmd(self, message):
        """Отправить случайное фото с yande.re и ссылку на него"""
        await message.edit("<b>Поиск случайного фото...</b>")

        try:
            url = "https://yande.re/post.json"
            params = {
                "limit": 1,
                "page": random.randint(1, 1000)
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data:
                photo_url = data[0]['file_url']

                if photo_url:
                    message_content = (f"<b>Случайное фото:</b>\n" 
                        f"<a href='{photo_url}'>Ссылка на оригинал</a>")
                    await self.client.send_file(message.to_id, photo_url, caption=message_content)
                    await message.delete()
                else:
                    await message.edit("<b>Не удалось найти фото.</b>")
            else:
                await message.edit("<b>Не удалось найти фото.</b>")
        except requests.RequestException as e:
            await message.edit(f"<b>Ошибка при запросе фото: {str(e)}</b>")
        except Exception as e:
            await message.edit(f"<b>Неизвестная ошибка: {str(e)}</b>")