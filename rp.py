# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
import aiohttp
from bs4 import BeautifulSoup
import re
import requests
from io import BytesIO
from pdf2image import convert_from_bytes

@loader.tds
class Rp(loader.Module):
    """Получает расписание пар и столовой для группы 1-ОТС-1 с сайта novkrp.ru"""
    strings = {
        "name": "Rp",
        "no_schedule": "<emoji document_id=5210952531676504517>❌</emoji> Не удалось найти расписание для группы 1-ОТС-1!",
        "no_canteen": "<emoji document_id=5210952531676504517>❌</emoji> Не удалось загрузить расписание столовой! {error}",
        "loading": "⏳ Загружаю расписание...",
        "schedule_found": "<emoji document_id=5431897022456145283>📆</emoji> Расписание для 1-ОТС-1 на {date}:\n{pairs}",
        "canteen_loading": "<b>Скачивание и обработка PDF...</b>"
    }

    # Время звонков для каждой пары
    pair_times = {
        "1 пара": {"start": "08:30", "end": "09:50"},
        "2 пара": {"start": "10:00", "end": "11:20"},
        "3 пара": {"start": "11:30", "end": "12:50"},
        "4 пара": {"start": "13:00", "end": "14:20"},
        "5 пара": {"start": "14:30", "end": "15:50"},
        "6 пара": {"start": "16:00", "end": "17:20"}
    }

    async def rpcmd(self, message):
        """Команда .rp - получает расписание для группы 1-ОТС-1"""
        await utils.answer(message, self.strings["loading"])

        url = "https://novkrp.ru/raspisanie.htm"
        group_variants = ["1-ОТС-1", "1 ОТС 1", "1-ОТС 1", "1 ОТС-1"]

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
                        if any(variant in header for variant in group_variants):
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
                        if not pair_number:
                            continue

                        pair_info = " ".join(cells[group_index].get_text(separator=" ").split())
                        if pair_info:
                            pair_info = re.sub(r"([а-яА-Я])([А-Я])", r"\1 \2", pair_info)
                            pair_info = re.sub(r"([а-яА-Я])\s*Ауд\.(\d+)", r"\1 Ауд.\2", pair_info)
                            # Добавляем время звонков
                            pair_time = self.pair_times.get(pair_number, {"start": "время", "end": "неизвестно"})
                            pairs.append(f"{pair_number} ({pair_time['start']}-{pair_time['end']}): {pair_info}")

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
            images = convert_from_bytes(response.content, first_page=1, last_page=1)
            if not images:
                raise Exception("PDF не содержит страниц")
            
            # Отправляем первую страницу как изображение без подписи
            with BytesIO() as output:
                images[0].save(output, format="JPEG")
                output.seek(0)
                await self._client.send_file(
                    message.peer_id,
                    output,
                    reply_to=message.reply_to_msg_id or message.id,
                )
            
            await message.delete()  # Удаляем исходное сообщение после отправки
        
        except Exception as e:
            await utils.answer(message, f"<b>Ошибка:</b> {str(e)}")