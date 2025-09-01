# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
import aiohttp
from bs4 import BeautifulSoup
import re
import requests
from io import BytesIO
from pdf2image import convert_from_bytes
from PIL import Image
import os # Import os for file operations
import asyncio # Import asyncio for sleep if needed

@loader.tds
class Rp(loader.Module):
    """Получает расписание пар и столовой для группы 2-ОТС-1 с сайта novkrp.ru"""
    strings = {
        "name": "Rp",
        "no_schedule": "<emoji document_id=5210952531676504517>❌</emoji> Не удалось найти расписание для группы 1-ОТС-1!",
        "no_canteen": "<emoji document_id=5210952531676504517>❌</emoji> Не удалось загрузить расписание столовой! {error}",
        "loading": "⏳ Загружаю расписание...",
        "schedule_found": "<emoji document_id=5431897022456145283>📆</emoji> Расписание для 1-ОТС-1 на {date}:\n{pairs}",
        "canteen_loading": "<b>Скачивание и обработка PDF...</b>",
        "temp_file_error": "<emoji document_id=5210952531676504517>❌</emoji> Ошибка при работе с временным файлом: {error}"
    }

    # Время звонков для каждой пары
    pair_times = {
        "1": {"start": "08:30", "end": "09:40"},
        "2": {"start": "09:50", "end": "11:00"},
        "3": {"start": "11:10", "end": "12:20"},
        "4": {"start": "12:30", "end": "13:40"},
        "5": {"start": "13:50", "end": "15:00"},
        "6": {"start": "15:10", "end": "16:20"}
    }

    async def rpcmd(self, message):
        """Команда .rp - получает расписание для группы 1-ОТС-1"""
        await utils.answer(message, self.strings["loading"])

        url = "https://novkrp.ru/raspisanie.htm"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        await utils.answer(message, self.strings["no_schedule"])
                        return
                    html = await resp.text()

                # Парсинг HTML
                soup = BeautifulSoup(html, "html.parser")

                # Ищем дату
                date_match = soup.find(string=re.compile(r"\d{2}\s[а-яА-Я]+\s2025г\."))
                if date_match:
                    date = re.sub(r"[,.]\s*", " ", date_match.strip())
                    date = re.sub(r"\s+", " ", date)
                else:
                    date = "неизвестную дату"

                # Ищем таблицу с расписанием
                tables = soup.find_all("table")
                if not tables:
                    await utils.answer(message, self.strings["no_schedule"])
                    return

                pairs = []
                for table in tables:
                    rows = table.find_all("tr")
                    if not rows:
                        continue

                    # Первая строка — заголовки
                    header_row = rows[0]
                    headers = [cell.get_text(strip=True) for cell in header_row.find_all(["th", "td"])]

                    # Ищем индекс столбца с группой
                    group_index = -1
                    for i, header in enumerate(headers):
                        if "2-ОТС-1" in header:
                            group_index = i
                            break

                    if group_index == -1:
                        continue

                    # Извлекаем пары из строк таблицы
                    for row in rows[1:]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) <= group_index:
                            continue

                        pair_number = cells[0].get_text(strip=True)
                        # Нормализуем номер пары (убираем "пара", "я", "-я" и пробелы)
                        pair_number = re.sub(r"[^0-6]", "", pair_number)
                        if not pair_number:
                            continue

                        pair_info = " ".join(cells[group_index].get_text(separator=" ").split())
                        if pair_info:
                            pair_info = re.sub(r"([а-яА-Я])([А-Я])", r"\1 \2", pair_info)
                            pair_info = re.sub(r"([а-яА-Я])\s*Ауд\.(\d+)", r"\1 Ауд.\2", pair_info)
                            # Добавляем время звонков
                            pair_time = self.pair_times.get(pair_number, {"start": "время", "end": "неизвестно"})
                            pairs.append(f"{pair_number} пара ({pair_time['start']}-{pair_time['end']}): {pair_info}")

                if not pairs:
                    await utils.answer(message, self.strings["no_schedule"])
                    return

                # Форматируем расписание пар
                formatted_pairs = "\n".join(pairs)
                reply = self.strings["schedule_found"].format(date=date, pairs=formatted_pairs)

                await utils.answer(message, reply)

            except Exception as e:
                await utils.answer(message, f"<emoji document_id=5210952531676504517>❌</emoji> Ошибка: {str(e)}")

    async def stcmd(self, message):
        """Скачать PDF и отправить первую страницу как изображение"""
        await utils.answer(message, self.strings["canteen_loading"])
        
        temp_file_path = "canteen_schedule_temp.jpg" # Define a temporary file name

        try:
            # Скачиваем PDF-файл
            pdf_url = "https://www.novkrp.ru/data/covid_pit.pdf"
            response = requests.get(pdf_url, timeout=15)
            
            if response.status_code != 200:
                raise Exception(f"Не удалось скачать PDF: статус {response.status_code}")
            
            # Проверяем размер файла
            content_length = len(response.content)
            if content_length > 10 * 1024 * 1024:  # 10 МБ
                raise Exception("PDF слишком большой (>10 МБ)")
            
            # Преобразуем PDF в изображения
            images = convert_from_bytes(response.content, first_page=1, last_page=1, dpi=300) 
            if not images:
                raise Exception("PDF не содержит страниц")
            
            # Сохраняем изображение во временный файл
            images[0].save(temp_file_path, format="JPEG")

            # Отправляем файл как фото
            await self._client.send_file(
                message.peer_id,
                file=temp_file_path, # Pass the path to the temporary file
                caption="", # No caption needed
                link_preview=False, # Sometimes helps prevent it from being treated as a document with a link
                reply_to=message.reply_to_msg_id or message.id,
                # Explicitly set as photo if the client supports it, but usually not needed for local files
                # if you want to be extra sure, you can try force_document=False, but for local files, 
                # Telethon typically infers the type correctly from the extension.
            )
            
            await message.delete()  # Удаляем исходное сообщение после отправки
        
        except Exception as e:
            await utils.answer(message, f"<b>Ошибка:</b> {str(e)}")
        finally:
            # Clean up: remove the temporary file
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    # Log or report error if file can't be removed, but don't stop execution
                    await utils.answer(message, self.strings["temp_file_error"].format(error=str(e)))

