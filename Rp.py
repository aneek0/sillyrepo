# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
import aiohttp
import re
import pymupdf
from bs4 import BeautifulSoup

@loader.tds
class Rp(loader.Module):
    """Получает расписание пар и столовой для группы 2-ОТС-1 с сайта novkrp.ru"""
    strings = {
        "name": "Rp",
        "no_schedule": "<emoji document_id=5210952531676504517>❌</emoji> Не удалось найти расписание для группы 2-ОТС-1!",
        "loading": "⏳ Загружаю расписание...",
        "schedule_found": "<emoji document_id=5431897022456145283>📆</emoji> Расписание для 2-ОТС-1 на {date}:\n{pairs}",
        "canteen_loading": "<b>⏳ Извлекаю расписание столовой из PDF...</b>",
    }

    DATE_PATTERN = re.compile(r"\d{2}\s[а-яА-Я]+\s2026г\.")
    PAIR_NUMBER_PATTERN = re.compile(r"[^0-7]")
    GROUP_PATTERN = re.compile(r'2[\s-]*ОТС[\s-]*1', re.IGNORECASE)
    TIME_PATTERN = re.compile(r'(\d+)\s+(\d{1,2}[:.]\d{2}\s*-\s*\d{1,2}[:.]\d{2})')
    OTHER_GROUPS_PATTERN = re.compile(r'\d+-[А-Я]+-\d+')

    regular_pair_times = {
        "1": {"start": "08:30", "end": "09:40"},
        "2": {"start": "09:50", "end": "11:00"},
        "3": {"start": "11:10", "end": "12:20"},
        "4": {"start": "12:30", "end": "13:40"},
        "5": {"start": "13:50", "end": "15:00"},
        "6": {"start": "15:10", "end": "16:20"},
        "7": {"start": "16:30", "end": "17:40"},
    }

    monday_pair_times = {
        "классный_час": {"start": "8:30", "end": "9:10"},
        "1": {"start": "9:10", "end": "10:20"},
        "2": {"start": "10:30", "end": "11:40"},
        "3": {"start": "11:50", "end": "13:00"},
        "4": {"start": "13:10", "end": "14:20"},
        "5": {"start": "14:30", "end": "15:40"},
        "6": {"start": "15:50", "end": "17:00"},
        "7": {"start": "17:10", "end": "18:20"},
    }

    def is_monday_schedule(self, date_text="", html_content=""):
        date_text = date_text or ""
        html_content = html_content or ""
        return any(k in (date_text + " " + html_content).lower() for k in ["понедельник", "monday"])

    async def rpcmd(self, message):
        await utils.answer(message, self.strings["loading"])
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://novkrp.ru/raspisanie.htm") as resp:
                    if resp.status != 200:
                        await utils.answer(message, self.strings["no_schedule"])
                        return
                    html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            date_match = soup.find(string=self.DATE_PATTERN)
            date = re.sub(r"\s+", " ", re.sub(r"[,.]\s*", " ", date_match.strip())) if date_match else "неизвестную дату"
            is_monday = self.is_monday_schedule(date, html)
            pair_times = self.monday_pair_times if is_monday else self.regular_pair_times
            pairs = self._extract_pairs(soup, pair_times, is_monday)
            if not pairs or (is_monday and len(pairs) == 1):
                await utils.answer(message, self.strings["no_schedule"])
                return
            day_info = " (понедельник - с классным часом)" if is_monday else ""
            await utils.answer(message, self.strings["schedule_found"].format(date=date + day_info, pairs="\n".join(pairs)))
        except Exception as e:
            await utils.answer(message, f"<emoji document_id=5210952531676504517>❌</emoji> Ошибка: {str(e)}")

    def _extract_pairs(self, soup, pair_times, is_monday):
        pairs = []
        if is_monday:
            ct = pair_times["классный_час"]
            pairs.append(f"Классный час ({ct['start']}-{ct['end']})")
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue
            headers = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
            gi = next((i for i, h in enumerate(headers) if "2-ОТС-1" in h), -1)
            if gi == -1:
                continue
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) <= gi:
                    continue
                pn = self.PAIR_NUMBER_PATTERN.sub("", cells[0].get_text(strip=True))
                if not pn:
                    continue
                pi = self._format_pair_info(cells[gi].get_text(separator=" "))
                if pi:
                    pt = pair_times.get(pn, {"start": "время", "end": "неизвестно"})
                    pairs.append(f"{pn} пара ({pt['start']}-{pt['end']}): {pi}")
        return pairs

    def _format_pair_info(self, text):
        if not text:
            return ""
        text = " ".join(text.split())
        text = re.sub(r"([а-яА-Я])([А-Я])", r"\1 \2", text)
        text = re.sub(r"([а-яА-Я])\s*Ауд\.(\d+)", r"\1 Ауд.\2", text)
        return text

    async def stcmd(self, message):
        await utils.answer(message, self.strings["canteen_loading"])
        try:
            full_text = await self._extract_pdf_text()
            if not full_text:
                raise Exception("Не удалось извлечь текст из PDF")
            result = self._find_group_schedule(full_text)
            if result:
                await utils.answer(message, result)
            else:
                await utils.answer(message, "<b>❌ Группа 2-ОТС-1 не найдена в расписании столовой</b>")
        except Exception as e:
            await utils.answer(message, f"<b>❌ Ошибка:</b> {str(e)}")

    async def _extract_pdf_text(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.novkrp.ru/data/covid_pit.pdf") as response:
                response.raise_for_status()
                data = await response.read()
                if len(data) > 10 * 1024 * 1024:
                    raise Exception("PDF слишком большой (>10 МБ)")
                doc = pymupdf.open(stream=data, filetype="pdf")
                text = "\n".join(page.get_text() for page in doc)
                doc.close()
                return text.strip()

    def _find_group_schedule(self, full_text):
        clean = re.sub(r'\s+', ' ', full_text)
        match = self.GROUP_PATTERN.search(clean)
        if match:
            before = clean[:match.start()]
            times = list(self.TIME_PATTERN.finditer(before))
            if times:
                last = times[-1]
                between = clean[last.end():match.start()]
                if not [g for g in self.OTHER_GROUPS_PATTERN.findall(between) if not self.GROUP_PATTERN.search(g)]:
                    return self._fmt_canteen(last.group(1), last.group(2))
        return self._find_context_schedule(full_text)

    def _find_context_schedule(self, full_text):
        lines = full_text.split('\n')
        for i, line in enumerate(lines):
            ls = line.strip()
            if not ls or not self.GROUP_PATTERN.search(ls):
                continue
            ctx = " ".join(lines[j].strip() for j in range(max(0, i - 3), i + 1))
            times = list(self.TIME_PATTERN.finditer(ctx))
            if not times:
                continue
            last = times[-1]
            after = ctx[last.end():].strip()
            if self.GROUP_PATTERN.search(after):
                gt = re.split(r'\d+\s+пара|\d+\s+\d{1,2}[:.]\d{2}', after)[0].strip()
                return self._fmt_canteen(last.group(1), last.group(2), gt)
        return None

    @staticmethod
    def _fmt_canteen(number, time, groups=""):
        parts = [f"<b>🍽 Расписание столовой для группы 2-ОТС-1:</b>\n", f"⏰ {number}. {time}"]
        if groups:
            cg = re.sub(r'\s+', ' ', groups).strip()
            if cg:
                parts.append(f"👥 {cg}")
        return "\n".join(parts)
