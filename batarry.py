# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import asyncio
import re
from .. import loader, utils

class BatteryStatusMod(loader.Module):
    strings = {"name": "BatteryStatusMod"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client
        self.monitoring = self.db.get(self.strings["name"], "monitoring", False)
        self.chat_id = self.db.get(self.strings["name"], "chat_id", None)
        
        # Если мониторинг был включен до перезагрузки, запускаем его снова
        if self.monitoring and self.chat_id:
            asyncio.ensure_future(self.battery_monitor())

    async def bcmd(self, message):
        """Показывает текущий уровень заряда батареи"""
        try:
            process = await asyncio.create_subprocess_shell(
                "su -c 'dumpsys battery | grep level'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if stderr:
                return await utils.answer(message, f"Ошибка: {stderr.decode('utf-8')}")

            battery_level = re.search(r'level: (\d+)', stdout.decode('utf-8')).group(1)
            await utils.answer(message, f"Текущий уровень заряда: {battery_level}%")
        except Exception as e:
            await utils.answer(message, f"Ошибка при получении уровня заряда: {str(e)}")

    async def b20cmd(self, message):
        """Включает мониторинг заряда батареи с уведомлениями каждый час"""
        if not self.monitoring:
            self.monitoring = True
            self.db.set(self.strings["name"], "monitoring", True)
            self.chat_id = message.chat_id
            self.db.set(self.strings["name"], "chat_id", self.chat_id)
            await utils.answer(message, "Мониторинг батареи включен. Уведомления будут отправляться каждый час.")
            asyncio.ensure_future(self.battery_monitor())
        else:
            self.monitoring = False
            self.db.set(self.strings["name"], "monitoring", False)
            await utils.answer(message, "Мониторинг батареи отключен.")

    async def battery_monitor(self):
        """Мониторинг уровня батареи с уведомлениями каждый час"""
        while self.monitoring:
            try:
                process = await asyncio.create_subprocess_shell(
                    "su -c 'dumpsys battery | grep level'",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if stderr:
                    await self.client.send_message(self.chat_id, f"Ошибка мониторинга: {stderr.decode('utf-8')}")
                    break

                battery_level = int(re.search(r'level: (\d+)', stdout.decode('utf-8')).group(1))

                await self.client.send_message(self.chat_id, f"🔋 Текущий уровень заряда: {battery_level}%")

                # Ожидаем 1 час перед следующим обновлением
                await asyncio.sleep(3600)

            except Exception as e:
                await self.client.send_message(self.chat_id, f"Ошибка мониторинга батареи: {str(e)}")
                break