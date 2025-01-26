# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import asyncio
import re
from .. import loader, utils
from aiogram.types import Message as AiogramMessage

@loader.tds
class BatteryStatusMod(loader.Module):
    """Показывает статус батареи и отправляет уведомления каждый час"""

    strings = {"name": "BatteryStatusMod"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client

        self.owner_id = (await client.get_me()).id  # ID владельца модуля
        self.monitoring = self.db.get(self.strings["name"], "monitoring", False)

        # Если мониторинг был включен до перезагрузки, запускаем его снова
        if self.monitoring:
            asyncio.ensure_future(self.battery_monitor())

    async def bcmd(self, message):
        """Показывает текущий уровень заряда батареи"""
        try:
            battery_level = await self.get_battery_level()
            if battery_level is not None:
                await self.inline.bot.send_message(
                    self.owner_id, f"🔋 Текущий уровень заряда: {battery_level}%"
                )
                await utils.answer(message, "🔋 Уровень заряда отправлен вам в ЛС ботом.")
            else:
                await utils.answer(message, "Ошибка при получении уровня заряда.")
        except Exception as e:
            await utils.answer(message, f"Ошибка: {str(e)}")

    async def b20cmd(self, message):
        """Включает мониторинг заряда батареи с уведомлениями каждый час"""
        if self.monitoring:
            await utils.answer(message, "Мониторинг уже включен.")
            return

        self.monitoring = True
        self.db.set(self.strings["name"], "monitoring", True)
        await utils.answer(
            message,
            "Мониторинг батареи включен. Уведомления будут отправляться вам в ЛС ботом каждый час.",
        )
        asyncio.ensure_future(self.battery_monitor())

    async def stopcmd(self, message):
        """Останавливает мониторинг заряда батареи"""
        if not self.monitoring:
            await utils.answer(message, "Мониторинг уже остановлен.")
            return

        self.monitoring = False
        self.db.set(self.strings["name"], "monitoring", False)
        await utils.answer(message, "Мониторинг батареи отключен.")

    async def battery_monitor(self):
        """Мониторинг уровня батареи с уведомлениями каждый час"""
        while self.monitoring:
            try:
                battery_level = await self.get_battery_level()
                if battery_level is not None:
                    await self.inline.bot.send_message(
                        self.owner_id, f"🔋 Текущий уровень заряда: {battery_level}%"
                    )
                else:
                    await self.inline.bot.send_message(
                        self.owner_id, "Ошибка при получении уровня заряда."
                    )
                await asyncio.sleep(3600)  # Проверяем каждый час
            except Exception as e:
                await self.inline.bot.send_message(
                    self.owner_id, f"Ошибка мониторинга батареи: {str(e)}"
                )
                break

    async def get_battery_level(self):
        """Получает текущий уровень заряда батареи"""
        try:
            process = await asyncio.create_subprocess_shell(
                "su -c 'dumpsys battery'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if stderr:
                return None

            output = stdout.decode("utf-8")
            match = re.search(r"level: (\d+)", output)
            if match:
                return int(match.group(1))
            else:
                return None
        except Exception:
            return None
            