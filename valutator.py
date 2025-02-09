# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils
import re
import logging

logger = logging.getLogger(__name__)

currency_patterns = [
    r"(\d+\s*[к]?)\s*(доллар|бакс|usd|евро|eur|рубл|р|rub|бел\.?\s*руб|бр|тг|tenge|кзт|юан|yuan|йен|jpy|гривн|uah|тон|ton)",
]

@loader.tds
class ValutatorMod(loader.Module):
    """Модуль для конвертации валют с помощью @Deltatale_Currency_Converter_Bot"""

    strings = {"name": "Valutator"}

    async def client_ready(self, client, db):
        self.client = client
        self.converter_bot = "@Deltatale_Currency_Converter_Bot"

    async def currcmd(self, message):
        """Отправляет текст после .curr боту для конвертации. Использование: .curr <сумма> <валюта>"""
        query = message.raw_text.replace(".curr", "").strip()
        if not query:
            await message.reply("Пожалуйста, укажите валюту для конвертации.")
            return
        await self.send_conversion_request(query, message)

    async def watcher(self, message):
        """Автоматически ищет валюты в сообщениях и отправляет запрос боту"""
        if message.raw_text.startswith(".autocurr"):
            return
        text = message.raw_text.lower()
        for pattern in currency_patterns:
            match = re.search(pattern, text)
            if match:
                query = match.group(0)
                await self.send_conversion_request(query, message)
                break

    async def autocurrcmd(self, message):
        """Включает автоматическую конвертацию валют в сообщениях. Использование: .autocurr"""
        await message.reply("Автоматическая конвертация валют включена.")

    async def send_conversion_request(self, query, message):
        query = re.sub(r"(\d+)\s*к", lambda m: str(int(m.group(1)) * 1000), query)
        async with self.client.conversation(self.converter_bot) as conv:
            await conv.send_message(query)
            response = await conv.get_response()
            await message.reply(response.text)
