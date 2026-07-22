# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
import aiohttp

@loader.tds
class AzuWeatherMod(loader.Module):
    """Получает прогноз погоды через OpenWeatherMap с кастомными эмодзи"""
    strings = {
        "name": "Weather",
        "no_api_key": "<emoji document_id=5210952531676504517>❌</emoji> Укажи API-ключ OpenWeatherMap в настройках (.config AzuWeather api_key <ключ>)",
        "no_city": "<emoji document_id=5210952531676504517>❌</emoji> Укажи город! Пример: .weather Москва или .weather -f Москва",
        "city_not_found": "<emoji document_id=5210952531676504517>❌</emoji> Город не найден!",
        "api_error": "<emoji document_id=5210952531676504517>❌</emoji> Ошибка API: {}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                "API-ключ OpenWeatherMap (https://home.openweathermap.org/api_keys)",
            )
        )

    async def wcmd(self, message):
        """Команда .w [-f] [-hf] <город> — погода. -f: прогноз на 5 дней, -hf: почасовой на 12ч"""
        args = utils.get_args(message)
        if not args:
            await utils.answer(message, self.strings["no_city"])
            return

        api_key = self.config["api_key"]
        if not api_key:
            await utils.answer(message, self.strings["no_api_key"])
            return

        f = "-f" in args
        hf = "-hf" in args
        city = " ".join(a for a in args if not a.startswith("-"))

        if not city:
            await utils.answer(message, self.strings["no_city"])
            return

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as session:
            try:
                async with session.get(
                    f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
                ) as resp:
                    if resp.status == 404:
                        await utils.answer(message, self.strings["city_not_found"])
                        return
                    resp.raise_for_status()
                    data = await resp.json()

                t = round(data["main"]["temp"])
                fl = round(data["main"]["feels_like"])
                h = data["main"]["humidity"]
                w = data["wind"]["speed"]
                desc = data["weather"][0]["description"].capitalize()
                city_name = data["name"]

                reply = (
                    f"<emoji document_id=5402477260982731644>☀️</emoji> Погода в городе {city_name}:\n"
                    f"<emoji document_id=5470049770997292425>🌡</emoji> Температура: {t}°C (ощущается как {fl}°C)\n"
                    f"<emoji document_id=5393512611968995988>💧</emoji> Влажность: {h}%\n"
                    f"<emoji document_id=5449885771420934013>🍃</emoji> Скорость ветра: {w} м/с\n"
                    f"<emoji document_id=5287571024500498635>☁️</emoji> Небо: {desc}"
                )

                if hf or f:
                    async with session.get(
                        f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=ru"
                    ) as resp:
                        if resp.status == 200:
                            fdata = await resp.json()

                            if hf:
                                for item in fdata["list"][:4]:
                                    time = item["dt_txt"].split(" ")[1][:5]
                                    temp = round(item["main"]["temp"])
                                    d = item["weather"][0]["description"].capitalize()
                                    reply += (
                                        f"\n\n<emoji document_id=5470049770997292425>🌡</emoji> {time}: {temp}°C"
                                        f"\n<emoji document_id=5287571024500498635>☁️</emoji> {d}"
                                    )

                            if f:
                                days = {}
                                for item in fdata["list"]:
                                    date = item["dt_txt"].split(" ")[0]
                                    if date not in days:
                                        days[date] = {
                                            "tmin": item["main"]["temp_min"],
                                            "tmax": item["main"]["temp_max"],
                                            "descs": [item["weather"][0]["description"].capitalize()],
                                        }
                                    else:
                                        d2 = days[date]
                                        d2["tmin"] = min(d2["tmin"], item["main"]["temp_min"])
                                        d2["tmax"] = max(d2["tmax"], item["main"]["temp_max"])
                                        d2["descs"].append(item["weather"][0]["description"].capitalize())

                                for i, (date, info) in enumerate(days.items()):
                                    if i >= 5:
                                        break
                                    avg = round((info["tmin"] + info["tmax"]) / 2)
                                    desc_day = info["descs"][len(info["descs"]) // 2]
                                    reply += (
                                        f"\n\n<emoji document_id=5431897022456145283>📆</emoji> {date}:\n"
                                        f"<emoji document_id=5470049770997292425>🌡</emoji> {avg}°C ({round(info['tmin'])}–{round(info['tmax'])}°C)\n"
                                        f"<emoji document_id=5287571024500498635>☁️</emoji> {desc_day}"
                                    )

                await utils.answer(message, reply)
            except Exception as e:
                await utils.answer(message, self.strings["api_error"].format(str(e)))
