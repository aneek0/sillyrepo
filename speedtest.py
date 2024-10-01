# requires: speedtest-cli

from typing import Tuple

import speedtest  # pylint: disable=import-self
from telethon import TelegramClient
from telethon.tl.custom import Message
from telethon.tl.functions.channels import JoinChannelRequest

from .. import loader, utils


# noinspection PyCallingNonCallable,PyAttributeOutsideInit
# pylint: disable=not-callable,attribute-defined-outside-init,invalid-name
@loader.tds
class SpeedtestMod(loader.Module):
    """Tests your internet speed via speedtest.net"""

    strings = {
        "name": "Speedtest",
        "author": "@nalinormods",
        "running": "🕑 <b>Checking your internet speed...</b>",
        "result": (
            "<b>⬇️ Download: <code>{download}</code> MBit/s</b>\n"
            "<b>⬆️ Upload: <code>{upload}</code> MBit/s</b>\n"
            "<b>🏓 Ping: <code>{ping}</code> ms</b>"
        ),
    }

    strings_ru = {
        "_cls_doc": "Проверяет скорость интернета на вашем сервере",
        "_cmd_doc_speedtest": "Проверить скорость интернета",
        "running": "🕑 <b>Проверяем скорость интернета...</b>",
        "result": (
            "<b>⬇️ Скачать: <code>{download}</code> МБит/с</b>\n"
            "<b>⬆️ Загрузить: <code>{upload}</code> МБит/с</b>\n"
            "<b>🏓 Пинг: <code>{ping}</code> мс</b>"
        ),
    }
    
    
    async def speedtestcmd(self, message: Message):
        """Run speedtest"""
        m = await utils.answer(message, self.strings("running"))
        results = await utils.run_sync(self.run_speedtest)
        await utils.answer(
            m,
            self.strings("result").format(
                download=round(results[0] / 1024 / 1024),
                upload=round(results[1] / 1024 / 1024),
                ping=round(results[2], 3),
            ),
        )

    @staticmethod
    def run_speedtest() -> Tuple[float, float, float]:
        """Speedtest using speedtest library"""
        s = speedtest.Speedtest()  # pylint: disable=no-member
        s.get_servers()
        s.get_best_server()
        s.download()
        s.upload()
        res = s.results.dict()
        return res["download"], res["upload"], res["ping"]