# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
import aiohttp

@loader.tds
class AzuWeatherMod(loader.Module):
    """Получает прогноз погоды через OpenWeatherMap с кастомными эмодзи"""
    strings = {
        "name": "AzuWeather",
        "no_api_key": "<emoji document_id=5210952531676504517>❌</emoji> Укажи API-ключ OpenWeatherMap в настройках (.config AzuWeather api_key <ключ>)",
        "no_city": "<emoji document_id=5210952531676504517>❌</emoji> Укажи город! Пример: .weather Москва или .weather -f Москва",
        "city_not_found": "<emoji document_id=5210952531676504517>❌</emoji> Город не найден!"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                None,
                lambda: "API-ключ от OpenWeatherMap",
                validator=loader.validators.String()
            )
        )

    async def weathercmd(self, message):
        """Команда .weather [-f] <город> - показывает погоду (с -f добавляет прогноз на 5 дней)"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_city"])
            return

        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return

        # Проверка флага -f
        forecast = "-f" in args
        city = args.replace("-f", "").strip()

        if not city:
            await utils.answer(message, self.strings["no_city"])
            return

        api_key = self.config["api_key"]

        # URL для текущей погоды
        current_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        # URL для прогноза на 5 дней (если нужен)
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=ru"

        async with aiohttp.ClientSession() as session:
            # Текущая погода
            try:
                async with session.get(current_url) as resp:
                    if resp.status != 200:
                        await utils.answer(message, self.strings["city_not_found"])
                        return
                    data = await resp.json()

                temperature = round(data["main"]["temp"])
                feels_like = round(data["main"]["feels_like"])
                humidity = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"]
                description = data["weather"][0]["description"].capitalize()
                city_name = data["name"]

                weather_info = (
                    f"<emoji document_id=5402477260982731644>☀️</emoji> Погода в городе {city_name.capitalize()}:\n"
                    f"<emoji document_id=5470049770997292425>🌡</emoji> Температура: {temperature}°C (ощущается как {feels_like}°C)\n"
                    f"<emoji document_id=5393512611968995988>💧</emoji> Влажность: {humidity}%\n"
                    f"<emoji document_id=5449885771420934013>🍃</emoji> Скорость ветра: {wind_speed} м/с\n"
                    f"<emoji document_id=5287571024500498635>☁️</emoji> Небо: {description}"
                )

                reply = weather_info

                # Прогноз на 5 дней, если есть флаг -f
                if forecast:
                    async with session.get(forecast_url) as resp:
                        if resp.status == 200:
                            forecast_data = await resp.json()
                            days = {}
                            for item in forecast_data["list"]:
                                date = item["dt_txt"].split(" ")[0]
                                if date not in days and "12:00:00" in item["dt_txt"]:
                                    days[date] = item

                            for date, item in list(days.items())[:5]:
                                temp_min = item["main"]["temp_min"]
                                temp_max = item["main"]["temp_max"]
                                temp_avg = round((temp_min + temp_max) / 2)  # Средняя температура с округлением
                                desc = item["weather"][0]["description"].capitalize()
                                forecast_info = (
                                    f"\n\n<emoji document_id=5431897022456145283>📆</emoji> {date}:\n"
                                    f"<emoji document_id=5470049770997292425>🌡</emoji> Температура: {temp_avg}°C\n"
                                    f"<emoji document_id=5287571024500498635>☁️</emoji> Небо: {desc}"
                                )
                                reply += forecast_info

                await utils.answer(message, reply)
            except Exception as e:
                await utils.answer(message, f"<emoji document_id=5210952531676504517>❌</emoji> Ошибка: {str(e)}")