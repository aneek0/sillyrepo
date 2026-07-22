# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
from datetime import datetime

@loader.tds
class RpG(loader.Module):
    """Получает расписание уроков для класса 11 A"""
    strings = {
        "name": "RpG",
        "schedule_found": "<emoji document_id=5431897022456145283>📆</emoji> 11A • {day}\n{lessons}"
    }
    
    def __init__(self):
        pass
    
    # Расписание звонков
    lesson_times = {
        "1": {"start": "08:30", "end": "09:15"},
        "2": {"start": "09:30", "end": "10:15"},
        "3": {"start": "10:30", "end": "11:15"},
        "4": {"start": "11:30", "end": "12:15"},
        "5": {"start": "12:30", "end": "13:15"},
        "6": {"start": "13:30", "end": "14:15"},
        "7": {"start": "14:30", "end": "15:15"}
    }
    
    # Фиксированное расписание для класса 11 A (обновлено)
    schedule = {
        "панядзелак": [
            ("1", "пр. навуч.", ""),
            ("2", "пр. навуч.", ""),
            ("3", "пр. навуч.", ""),
            ("4", "пр. навуч.", ""),
            ("5", "пр. навуч.", ""),
            ("6", "пр. навуч.", "")
        ],
        "аўторак": [
            ("1", "ФКіЗ", "201"),
            ("2", "бел. мова", "304"),
            ("3", "геаграфия", "301"),
            ("4", "хімия", "217"),
            ("5", "бел. літ.", "304"),
            ("6", "матэмматика", "202"),
            ("7", "гіст. Бел.", "302")
        ],
        "серада": [
            ("1", "гіст. Бел.", "208"),
            ("2", "фіз.", "310"),
            ("3", "ФКіЗ (п)", "201"),
            ("4", "матэм.", "202"),
            ("5", "рус. мова", "309"),
            ("6", "біял.", "208"),
            ("7", "англ. мова", "217/305")
        ],
        "чацвер": [
            ("1", "рус. літ.", "301"),
            ("2", "фіз.", "310"),
            ("3", "рус. мова", "306"),
            ("4", "біял.", "208"),
            ("5", "інф./англ.", "309/305"),
            ("6", "матэматика", "202"),
            ("7", "бел. літ.", "304")
        ],
        "пятніца": [
            ("1", "хімия", "217"),
            ("2", "астрономия", "310"),
            ("3", "англ./інф.", "301/309"),
            ("4", "ФКіЗ", "201"),
            ("5", "Обществоведение", "302"),
            ("6", "матэматика", "202")
        ]
    }
    
    def get_day_name(self, day_num):
        """Возвращает название дня недели на белорусском"""
        days = ["панядзелак", "аўторак", "серада", "чацвер", "пятніца", "субота", "нядзеля"]
        return days[day_num] if 0 <= day_num < 7 else "панядзелак"
    
    def get_schedule_day(self):
        """Определяет, какое расписание показывать в зависимости от дня недели и времени"""
        now = datetime.now()
        weekday = now.weekday()  # 0 = понедельник, 6 = воскресенье
        current_time = now.strftime("%H:%M")
        
        # Если суббота (5) или воскресенье (6) - показываем расписание на понедельник
        if weekday >= 5:
            return 0  # понедельник
        
        # Если понедельник-пятница (0-4)
        # Проверяем, закончился ли последний урок (после 15:15)
        last_lesson_end = "15:15"
        if current_time > last_lesson_end:
            # Показываем расписание на следующий день
            next_day = (weekday + 1) % 5  # 0-4 (понедельник-пятница)
            return next_day
        else:
            # Показываем расписание на сегодня
            return weekday
    
    async def rpgcmd(self, message):
        """Команда .rpg - получает расписание для класса 11 A"""
        args = utils.get_args_raw(message).lower().strip()
        
        # Если указан аргумент - используем его
        if args and args in self.schedule:
            day_name = args
        else:
            # Автоматически определяем день расписания
            schedule_day_num = self.get_schedule_day()
            day_name = self.get_day_name(schedule_day_num)
        
        if day_name not in self.schedule:
            await utils.answer(message, f"<emoji document_id=5210952531676504517>❌</emoji> Расклад урокаў на {day_name} не знойдзен!")
            return
        
        # Формируем список уроков
        lessons_list = []
        for lesson_num, subject, room in self.schedule[day_name]:
            time_info = self.lesson_times.get(lesson_num, {"start": "", "end": ""})
            room_info = f" ({room})" if room else ""
            lessons_list.append(
                f"{lesson_num} урок ({time_info['start']}-{time_info['end']}): {subject}{room_info}"
            )
        
        # Формируем ответ
        reply = self.strings["schedule_found"].format(
            day=day_name.capitalize(),
            lessons="\n".join(lessons_list)
        )
        await utils.answer(message, reply)