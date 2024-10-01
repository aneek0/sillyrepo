from .. import loader, utils

class TimeConverter(loader.Module):
    """Конвертирует время из одного формата в другой"""

    strings = {"name": "TimeConverter"}

    async def ctcmd(self, message):
        """.ct <time> - Конвертировать время (например, 10m, 1440m, 2h)"""

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "Пожалуйста, предоставьте значение для конвертации (например, 10m, 1440m, 2h).")
            return

        unit = args[-1].lower()
        value_str = args[:-1]

        if unit == 'o' and value_str.endswith('m'):
            unit = 'mo'
            value_str = value_str[:-1]
        elif unit == 'y':
            pass
        else:
            try:
                value = int(value_str)
            except ValueError:
                await utils.answer(message, "Некорректное значение. Используйте числовое значение и единицу времени (например, 10m, 1440m, 2h).")
                return

        try:
            value = int(value_str)
        except ValueError:
            await utils.answer(message, "Некорректное значение. Используйте числовое значение и единицу времени (например, 10m, 1440m, 2h).")
            return

        if unit == 's':
            seconds = value
            minutes = value / 60
            hours = value / 3600
            days = value / 86400
            months = value / (86400 * 30)
            years = value / (86400 * 365)
        elif unit == 'm':
            seconds = value * 60
            minutes = value
            hours = value / 60
            days = value / 1440
            months = value / (1440 * 30)
            years = value / (1440 * 365)
        elif unit == 'h':
            seconds = value * 3600
            minutes = value * 60
            hours = value
            days = value / 24
            months = value / (24 * 30)
            years = value / (24 * 365)
        elif unit == 'd':
            seconds = value * 86400
            minutes = value * 1440
            hours = value * 24
            days = value
            months = value / 30
            years = value / 365
        elif unit == 'mo':
            seconds = value * 86400 * 30
            minutes = value * 1440 * 30
            hours = value * 24 * 30
            days = value * 30
            months = value
            years = value / 12
        elif unit == 'y':
            seconds = value * 86400 * 365
            minutes = value * 1440 * 365
            hours = value * 24 * 365
            days = value * 365
            months = value * 12
            years = value
        else:
            await utils.answer(message, "Некорректная единица времени. Используйте 's' для секунд, 'm' для минут, 'h' для часов, 'd' для дней, 'mo' для месяцев, 'y' для лет.")
            return

        response = (
            f"<b>Время конвертировано:</b>\n"
            f"<b>{seconds} секунд</b>\n"
            f"<b>{minutes:.2f} минут</b>\n"
            f"<b>{hours:.2f} часов</b>\n"
            f"<b>{days:.2f} дней</b>\n"
            f"<b>{months:.2f} месяцев</b>\n"
            f"<b>{years:.2f} лет</b>"
        )

        await utils.answer(message, response)