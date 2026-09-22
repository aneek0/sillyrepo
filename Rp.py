# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
import aiohttp
import re
import pymupdf

@loader.tds
class Rp(loader.Module):
    """Получает расписание пар и столовой для группы 3-ОТС-1 с novkrp.gosuslugi.ru (PDF)"""
    strings = {
        "name": "Rp",
        "no_schedule": "<emoji document_id=5210952531676504517>❌</emoji> Не удалось найти расписание для группы 3-ОТС-1!",
        "loading": "⏳ Загружаю расписание...",
        "schedule_found": "<emoji document_id=5431897022456145283>📆</emoji> Расписание для 3-ОТС-1 на {date}:\n{pairs}",
        "canteen_loading": "<b>⏳ Загружаю график питания...</b>",
        "not_found_canteen": "<b>❌ Группа 3-ОТС-1 не найдена в графике питания</b>",
    }

    BASE_URL = "https://novkrp.gosuslugi.ru"
    SCHEDULE_PAGE = BASE_URL + "/grafik-zanyatiy/"

    GROUP_RE = re.compile(r"(?<![\d-])3[\s-]*ОТС[\s-]*1(?![\d-])", re.IGNORECASE)
    GROUP_ID = "3-ОТС-1"
    DATE_RE = re.compile(r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})\s*г?", re.IGNORECASE)
    PAIR_LABEL_RE = re.compile(r"^\s*(\d{1,2})\s*пара\s*$")
    CLASS_HOUR_RE = re.compile(r"класс[сн]\.??\s*час", re.IGNORECASE)
    TIME_SLOT_RE = re.compile(
        r"^\s*(\d{1,2})\s*\n\s*(\d{1,2}[:.]\d{2}\s*[-–—]\s*\d{1,2}[:.]\d{2})\s*\n\s*([^\n]+)", re.M
    )
    TIME_RE = re.compile(r"(\d{1,2})\s+(\d{1,2}[:.]\d{2}\s*[-–—]\s*\d{1,2}[:.]\d{2})")
    GROUP_TOKEN_RE = re.compile(r"\d{1,2}-[А-ЯЁ]{2,5}-\d{1,2}")
    OTHER_GROUP_RE = re.compile(r"(?<![\d-])\d[\s-]*[А-ЯЁ]{2,}[\s-]*\d(?![\d-])", re.IGNORECASE)

    pair_times = {
        "1": ("09:10", "10:10"),
        "2": ("10:20", "11:20"),
        "3": ("11:30", "12:30"),
        "4": ("12:40", "13:40"),
        "5": ("13:50", "14:50"),
        "6": ("15:00", "16:00"),
        "7": ("16:10", "17:10"),
    }

    async def rpcmd(self, message):
        """Расписание пар для 3-ОТС-1"""
        await utils.answer(message, self.strings["loading"])
        try:
            data = await self._fetch_pdf("schedule")
            full_text = self._pdf_text(data)
            date = self._parse_date(full_text)
            pairs = self._extract_pairs(data)
            if not pairs:
                await utils.answer(message, self.strings["no_schedule"])
                return
            await utils.answer(
                message,
                self.strings["schedule_found"].format(date=date, pairs="\n".join(pairs)),
            )
        except Exception as e:
            await utils.answer(message, f"<emoji document_id=5210952531676504517>❌</emoji> Ошибка: {e}")

    async def stcmd(self, message):
        """График питания для 3-ОТС-1"""
        await utils.answer(message, self.strings["canteen_loading"])
        try:
            data = await self._fetch_pdf("canteen")
            full_text = self._pdf_text(data)
            date, _ = self._parse_date(full_text)
            result = self._find_group_slot(full_text)
            if result:
                number, time, groups = result
                parts = [
                    f"<b>🍽 График питания для группы {self.GROUP_ID} на {date}:</b>\n",
                    f"⏰ Слот {number}: {time}",
                ]
                if groups:
                    parts.append(f"👥 {groups}")
                await utils.answer(message, "\n".join(parts))
            else:
                await utils.answer(message, self.strings["not_found_canteen"])
        except Exception as e:
            await utils.answer(message, f"<b>❌ Ошибка:</b> {e}")

    # ---------- network ----------

    async def _fetch_pdf(self, kind):
        """Скачивает PDF. kind: 'schedule' | 'canteen'.
        Сначала пробует прямые ссылки на текущую дату, иначе ищет на странице расписания."""
        today = self._local_today()
        candidates = self._url_candidates(today, kind)
        async with aiohttp.ClientSession() as session:
            for url in candidates:
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            return await resp.read()
                except aiohttp.ClientError:
                    continue
            html = await self._get_page_text(session, self.SCHEDULE_PAGE)
            links = self._doc_links(html, kind)
            for url in links:
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            return await resp.read()
                except aiohttp.ClientError:
                    continue
        raise Exception("Не удалось скачать PDF (проверьте, опубликовано ли расписание)")

    @staticmethod
    def _local_today():
        import datetime

        return datetime.date.today()

    def _url_candidates(self, day, kind):
        """Прямые ссылки на сегодняшнюю дату и пару дней вокруг неё."""
        suffix = "_pitanie" if kind == "canteen" else ""
        urls = []
        import datetime

        for delta in (0, -1, 1, -2, 2):
            d = day + datetime.timedelta(days=delta)
            urls.append(f"{self.BASE_URL}/netcat_files/49/315/{d.day:02d}.{d.month:02d}{suffix}.pdf")
        return urls

    async def _get_page_text(self, session, url):
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    def _doc_links(self, html, kind):
        """Вытаскивает ссылки на PDF со страницы расписания (ищет 'питание' в названии)."""
        links = re.findall(r'href="([^"]+\.pdf[^"]*)"', html or "")
        out = []
        for link in links:
            if not link.startswith("http"):
                link = self.BASE_URL + link
            is_canteen = "питани" in link.lower() or "pitanie" in link.lower()
            if (kind == "canteen") == is_canteen:
                if link not in out:
                    out.append(link)
        return out

    # ---------- pdf ----------

    @staticmethod
    def _pdf_text(data):
        if len(data) > 15 * 1024 * 1024:
            raise Exception("PDF слишком большой (>15 МБ)")
        doc = pymupdf.open(stream=data, filetype="pdf")
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()

    def _parse_date(self, text):
        """Строка даты из текста PDF. Fallback - локальная дата."""
        head = text[:400]
        m = self.DATE_RE.search(head)
        if not m:
            # дата может быть в таблице, ищем по всему тексту
            m = self.DATE_RE.search(text)
        if m:
            return f"{m.group(1)} {m.group(2).lower()} {m.group(3)}"
        import datetime

        now = datetime.date.today()
        months = [
            "января", "февраля", "марта", "апреля", "мая", "июня", "июля",
            "августа", "сентября", "октября", "ноября", "декабря",
        ]
        return f"{now.day} {months[now.month - 1]} {now.year}"

    # ---------- расписание ----------

    def _extract_pairs(self, data):
        """Основной путь: таблицы PDF. Fallback: текстовая разметка."""
        pairs = []
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
            try:
                for page in doc:
                    for table in page.find_tables().tables:
                        pairs.extend(self._pairs_from_table(table.extract()))
                        if pairs:
                            break
                    if pairs:
                        break
            finally:
                doc.close()
        except Exception:
            pass
        if not pairs:
            pairs = self._pairs_from_text(self._pdf_text(data), data)
        return pairs

    def _pairs_from_table(self, rows):
        pairs = []
        if not rows:
            return pairs
        header = [(c or "").replace("\n", "").strip() for c in rows[0]]
        gi = next((i for i, h in enumerate(header) if self.GROUP_RE.fullmatch(h)), None)
        if gi is None:
            return pairs
        for row in rows[1:]:
            label = (row[0] or "").strip()
            if self.CLASS_HOUR_RE.search(label):
                continue
            m = self.PAIR_LABEL_RE.match(label)
            if not m:
                continue
            cell = row[gi] if gi < len(row) else ""
            info = self._format_pair_info(cell)
            if not info:
                continue
            pn = m.group(1)
            pt = self.pair_times.get(pn, ("время", "неизвестно"))
            pairs.append(f"{pn} пара ({pt[0]}-{pt[1]}): {info}")
        return pairs

    def _pairs_from_text(self, text, data):
        """Fallback: колонки по заголовкам групп + строки 'N пара' по геометрии слов."""
        pairs = []
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
        except Exception:
            return []
        try:
            for page in doc:
                words = page.get_text("words")
                col_heads = sorted(
                    ((w[0] + w[2]) / 2, w[4])
                    for w in words
                    if self.GROUP_RE.fullmatch(w[4])
                )
                if not col_heads:
                    continue
                gx = col_heads[0][0]
                # метки строк: слово "пара" (номер отдельным словом ниже) или "1 пара" целиком
                para_words = [w for w in words if w[4] == "пара"]
                # строки: слово "пара", под ним номер пары отдельным словом
                row_starts = []
                for w in para_words:
                    v = next(
                        (
                            v
                            for v in words
                            if v[0] < w[0] + 2 and 0 <= v[1] - w[3] < 30 and re.fullmatch(r"\d{1,2}", v[4])
                        ),
                        None,
                    )
                    if v:
                        row_starts.append((v[3], v[4]))
                row_starts.sort()
                col_toks = sorted(
                    (w for w in words if w[4] != "пара" and abs((w[0] + w[2]) / 2 - gx) < 30),
                    key=lambda w: (w[1], w[0]),
                )
                for i, (y, num) in enumerate(row_starts):
                    y2 = row_starts[i + 1][0] if i + 1 < len(row_starts) else 10 ** 9
                    # берём токены от начала строки; разрыв > 14pt (пустая строка ячейки) завершает её
                    cell = [t for t in col_toks if t[1] >= y - 3 and t[1] < y2]
                    lines = []
                    last_y = None
                    for t in cell:
                        if last_y is not None and t[1] - last_y > 14:
                            break
                        lines.append(t)
                        last_y = t[1]
                    info = self._format_pair_info(" ".join(t[4] for t in lines))
                    if not info:
                        continue
                    pt = self.pair_times.get(num, ("время", "неизвестно"))
                    pairs.append(f"{num} пара ({pt[0]}-{pt[1]}): {info}")
        finally:
            doc.close()
        return pairs

    def _format_pair_info(self, cell_text):
        if not cell_text:
            return ""
        text = " ".join(str(cell_text).split())
        text = re.sub(r"\b([АМ])\s*ДК\b", r"\1ДК", text)
        text = re.sub(r"(?<=[а-яё])(?=[А-ЯЁ])|(?<=[А-ЯЁ]{2})(?=[А-ЯЁ][а-яё])", " ", text)
        text = re.sub(r"([а-яА-ЯёЁ])\s*Ауд\.\s*(\d+)", r"\1 Ауд.\2", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # ---------- столовая ----------

    def _find_group_slot(self, full_text):
        """Ищет слот питания группы. Основной путь - слот-строки таблицы."""
        for m in self.TIME_SLOT_RE.finditer(full_text):
            groups = " ".join(m.group(3).split())
            if self.GROUP_RE.search(groups):
                return m.group(1), m.group(2).replace(".", ":").replace(" ", ""), groups
        clean = re.sub(r"\s+", " ", full_text)
        gm = self.GROUP_RE.search(clean)
        if gm:
            before = clean[: gm.start()]
            times = list(self.TIME_RE.finditer(before))
            if times:
                last = times[-1]
                between = clean[last.end(): gm.start()]
                if not [g for g in self.OTHER_GROUP_RE.findall(between) if not self.GROUP_RE.search(g)]:
                    return last.group(1), last.group(2).replace(".", ":").replace(" ", ""), ""
        return None
