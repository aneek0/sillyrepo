# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
import aiohttp
import re
import os
import tempfile
import pymupdf
from bs4 import BeautifulSoup

@loader.tds
class Rp(loader.Module):
    """Получает расписание пар и столовой для группы 2-ОТС-1 с сайта novkrp.ru"""
    strings = {
        "name": "Rp",
        "no_schedule": "<emoji document_id=5210952531676504517>❌</emoji> Не удалось найти расписание для группы 2-ОТС-1!",
        "no_canteen": "<emoji document_id=5210952531676504517>❌</emoji> Не удалось загрузить расписание столовой! {error}",
        "loading": "⏳ Загружаю расписание...",
        "schedule_found": "<emoji document_id=5431897022456145283>📆</emoji> Расписание для 2-ОТС-1 на {date}:\n{pairs}",
        "canteen_loading": "<b>⏳ Извлекаю расписание столовой из PDF...</b>",
        "temp_file_error": "<emoji document_id=5210952531676504517>❌</emoji> Ошибка при работе с временным файлом: {error}"
    }
    
    def __init__(self):
        super().__init__()
        # Создаем директорию static, если её нет
        static_dir = "/root/Heroku/static"
        if not os.path.exists(static_dir):
            try:
                os.makedirs(static_dir, exist_ok=True)
            except Exception:
                pass  # Игнорируем ошибки создания директории
    
    # Константы для регулярных выражений
    DATE_PATTERN = re.compile(r"\d{2}\s[а-яА-Я]+\s2026г\.")
    PAIR_NUMBER_PATTERN = re.compile(r"[^0-7]")
    GROUP_PATTERNS = [
        re.compile(r'2-ОТС\s*-?\s*1', re.IGNORECASE),
        re.compile(r'2\s*-\s*ОТС\s*-\s*1', re.IGNORECASE),
        re.compile(r'2-ОТС-1', re.IGNORECASE),
        re.compile(r'2\s+ОТС\s+1', re.IGNORECASE)
    ]
    TIME_PATTERN = re.compile(r'(\d+)\s+(\d{1,2}[:.]\d{2}\s*-\s*\d{1,2}[:.]\d{2})')
    OTHER_GROUPS_PATTERN = re.compile(r'\d+-[А-Я]+-\d+')

    # Расписание звонков для обычных дней (вторник-суббота)
    regular_pair_times = {
        "1": {"start": "08:30", "end": "09:40"},
        "2": {"start": "09:50", "end": "11:00"},
        "3": {"start": "11:10", "end": "12:20"},
        "4": {"start": "12:30", "end": "13:40"},
        "5": {"start": "13:50", "end": "15:00"},
        "6": {"start": "15:10", "end": "16:20"},
        "7": {"start": "16:30", "end": "17:40"}
    }

    # Расписание звонков для понедельника (с классным часом)
    monday_pair_times = {
        "классный_час": {"start": "8:30", "end": "9:10"},
        "1": {"start": "9:10", "end": "10:20"},
        "2": {"start": "10:30", "end": "11:40"},
        "3": {"start": "11:50", "end": "13:00"},
        "4": {"start": "13:10", "end": "14:20"},
        "5": {"start": "14:30", "end": "15:40"},
        "6": {"start": "15:50", "end": "17:00"},
        "7": {"start": "17:10", "end": "18:20"}
    }

    def is_monday_schedule(self, date_text="", html_content=""):
        """Определяет, нужно ли показывать расписание звонков для понедельника"""
        # Защита от None
        date_text = date_text or ""
        html_content = html_content or ""
        return any(keyword in (date_text + " " + html_content).lower() 
                  for keyword in ["понедельник", "monday"])

    def get_pair_times(self, is_monday=False):
        """Возвращает расписание звонков"""
        return self.monday_pair_times if is_monday else self.regular_pair_times

    async def rpcmd(self, message):
        """Команда .rp - получает расписание для группы 2-ОТС-1"""
        await utils.answer(message, self.strings["loading"])

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://novkrp.ru/raspisanie.htm") as resp:
                    if resp.status != 200:
                        await utils.answer(message, self.strings["no_schedule"])
                        return
                    html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            
            # Извлекаем дату
            date_match = soup.find(string=self.DATE_PATTERN)
            date = re.sub(r"\s+", " ", re.sub(r"[,.]\s*", " ", date_match.strip())) if date_match else "неизвестную дату"

            # Определяем тип расписания
            is_monday = self.is_monday_schedule(date, html)
            pair_times = self.get_pair_times(is_monday)

            # Извлекаем пары
            pairs = self._extract_pairs(soup, pair_times, is_monday)
            
            if not pairs or (is_monday and len(pairs) == 1):
                await utils.answer(message, self.strings["no_schedule"])
                return

            # Формируем ответ
            day_info = " (понедельник - с классным часом)" if is_monday else ""
            reply = self.strings["schedule_found"].format(
                date=date + day_info, 
                pairs="\n".join(pairs)
            )
            await utils.answer(message, reply)

        except Exception as e:
            await utils.answer(message, f"<emoji document_id=5210952531676504517>❌</emoji> Ошибка: {str(e)}")

    def _extract_pairs(self, soup, pair_times, is_monday):
        """Извлекает пары из HTML"""
        pairs = []
        
        # Добавляем классный час для понедельника
        if is_monday:
            class_time = pair_times["классный_час"]
            pairs.append(f"Классный час ({class_time['start']}-{class_time['end']})")

        # Ищем таблицы с расписанием
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue

            # Находим индекс столбца с группой
            headers = [cell.get_text(strip=True) for cell in rows[0].find_all(["th", "td"])]
            group_index = next((i for i, header in enumerate(headers) if "2-ОТС-1" in header), -1)
            
            if group_index == -1:
                continue

            # Извлекаем пары
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= group_index:
                    continue

                pair_number = self.PAIR_NUMBER_PATTERN.sub("", cells[0].get_text(strip=True))
                if not pair_number:
                    continue

                pair_info = self._format_pair_info(cells[group_index].get_text(separator=" "))
                if pair_info:
                    pair_time = pair_times.get(pair_number, {"start": "время", "end": "неизвестно"})
                    pairs.append(f"{pair_number} пара ({pair_time['start']}-{pair_time['end']}): {pair_info}")

        return pairs

    def _format_pair_info(self, text):
        """Форматирует информацию о паре"""
        if not text:
            return ""
        
        # Очищаем и форматируем текст
        text = " ".join(text.split())
        text = re.sub(r"([а-яА-Я])([А-Я])", r"\1 \2", text)
        text = re.sub(r"([а-яА-Я])\s*Ауд\.(\d+)", r"\1 Ауд.\2", text)
        return text

    async def stcmd(self, message):
        """Извлечь расписание столовой для группы 2-ОТС-1 из PDF"""
        await utils.answer(message, self.strings["canteen_loading"])

        try:
            # Скачиваем и извлекаем текст из PDF
            full_text = await self._extract_pdf_text()
            if not full_text:
                raise Exception("Не удалось извлечь текст из PDF")
            
            # Ищем расписание для группы
            result = self._find_group_schedule(full_text)
            if result:
                await utils.answer(message, result)
            else:
                await utils.answer(message, "<b>❌ Группа 2-ОТС-1 не найдена в расписании столовой</b>")
        
        except Exception as e:
            await utils.answer(message, f"<b>❌ Ошибка:</b> {str(e)}")

    async def _extract_pdf_text(self):
        """Извлекает текст из PDF файла используя pymupdf"""
        pdf_url = "https://www.novkrp.ru/data/covid_pit.pdf"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    response.raise_for_status()
                    
                    # Проверяем размер файла по заголовку Content-Length
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > 10 * 1024 * 1024:  # 10 МБ
                        raise Exception("PDF слишком большой (>10 МБ)")
                    
                    # Читаем содержимое
                    content_data = await response.read()
                    if len(content_data) > 10 * 1024 * 1024:  # 10 МБ
                        raise Exception("PDF слишком большой (>10 МБ)")
                    
                    # Используем pymupdf для извлечения текста
                    # Всегда используем временный файл для надежности
                    pdf_document = None
                    tmp_path = None
                    try:
                        # Сохраняем PDF во временный файл
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                            tmp_file.write(content_data)
                            tmp_path = tmp_file.name
                        
                        # Открываем PDF из файла (более надежный способ)
                        # Пробуем разные способы открытия
                        pdf_document = None
                        try:
                            # Пробуем использовать метод open напрямую
                            pdf_document = pymupdf.open(tmp_path)
                        except (AttributeError, TypeError) as e:
                            # Если open не работает, пробуем Document
                            try:
                                pdf_document = pymupdf.Document(tmp_path)
                            except (AttributeError, TypeError):
                                raise Exception(f"pymupdf не поддерживает открытие PDF файлов. Ошибка: {str(e)}")
                        except Exception as e:
                            # Если это другая ошибка, пробрасываем дальше
                            if "has no attribute 'open'" in str(e) or "module 'fitz' has no attribute 'open'" in str(e):
                                raise Exception(f"Ошибка: установлен старый пакет fitz. Удалите его: pip uninstall fitz && pip install pymupdf")
                            raise
                        
                        full_text = ""
                        
                        # Извлекаем текст со всех страниц
                        for page_num in range(pdf_document.page_count):
                            page = pdf_document[page_num]
                            text = page.get_text()
                            if text:
                                full_text += text + "\n"
                        
                        pdf_document.close()
                        
                        # Удаляем временный файл, если он был создан
                        if tmp_path and os.path.exists(tmp_path):
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass
                        
                        return full_text.strip()
                        
                    except Exception as e:
                        # Удаляем временный файл в случае ошибки
                        if tmp_path and os.path.exists(tmp_path):
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass
                        raise Exception(f"Ошибка pymupdf: {str(e)}")
            
        except Exception as e:
            raise Exception(f"Ошибка загрузки PDF: {str(e)}")

    def _find_group_schedule(self, full_text):
        """Ищет расписание для группы 2-ОТС-1"""
        clean_text = re.sub(r'\s+', ' ', full_text)
        
        # Ищем группу и связанное с ней время
        for pattern in self.GROUP_PATTERNS:
            match = pattern.search(clean_text)
            if match:
                # Ищем время перед группой
                text_before = clean_text[:match.start()]
                time_matches = list(self.TIME_PATTERN.finditer(text_before))
                
                if time_matches:
                    last_match = time_matches[-1]
                    found_number = last_match.group(1)
                    found_time = last_match.group(2)
                    
                    # Проверяем, что между временем и группой нет других групп
                    text_between = clean_text[last_match.end():match.start()]
                    other_groups = [g for g in self.OTHER_GROUPS_PATTERN.findall(text_between) 
                                  if not pattern.search(g)]
                    
                    if not other_groups:
                        return self._format_canteen_result(found_number, found_time)
        
        # Если точное время не найдено, ищем в контексте строк
        return self._find_context_schedule(full_text)

    def _find_context_schedule(self, full_text):
        """Ищет расписание в контексте строк"""
        lines = full_text.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Проверяем, есть ли наша группа в этой строке
            if any(pattern.search(line_stripped) for pattern in self.GROUP_PATTERNS):
                # Собираем контекст из нескольких строк
                context_start = max(0, i - 3)
                context_text = " ".join(lines[j].strip() for j in range(context_start, i + 1))
                
                # Ищем время в контексте
                time_matches = list(self.TIME_PATTERN.finditer(context_text))
                if time_matches:
                    last_match = time_matches[-1]
                    number = last_match.group(1)
                    time = last_match.group(2)
                    
                    # Проверяем, что группа действительно связана с этим временем
                    after_time = context_text[last_match.end():].strip()
                    if any(pattern.search(after_time) for pattern in self.GROUP_PATTERNS):
                        groups_text = re.split(r'\d+\s+пара|\d+\s+\d{1,2}[:.]\d{2}', after_time)[0].strip()
                        return self._format_canteen_result(number, time, groups_text)
        
        return None

    def _format_canteen_result(self, number, time, groups=""):
        """Форматирует результат расписания столовой"""
        result_parts = [
            "<b>🍽 Расписание столовой для группы 2-ОТС-1:</b>\n",
            f"⏰ {number}. {time}"
        ]
        
        if groups:
            clean_groups = re.sub(r'\s+', ' ', groups).strip()
            if clean_groups:
                result_parts.append(f"👥 {clean_groups}")
        
        return "\n".join(result_parts)