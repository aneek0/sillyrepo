#meta developer: @thisLyomi & @AmekaMods

import asyncio
from telethon import events
from .. import loader, utils

@loader.tds
class LyaMusic(loader.Module):
    """Модуль для поиска музыки, основанный на боте @LyaDownbot"""
    
    strings = {
        "name": "LyaMusic",
        "searching": "<b><emoji document_id=5188311512791393083>🔎</emoji> Ищу музыку...</b>",
        "no_results": "<b><emoji document_id=5210952531676504517>❌</emoji> Произошла ошибка. Попробуйте указать точное название трека, либо трек невозможно найти.</b>",
        "loading": "<b><emoji document_id=5451732530048802485>⏳</emoji> Загрузка трека...</b>",
        "enter_name": "<b><emoji document_id=5210952531676504517>❌</emoji> Введите название трека </b>"
    }
    strings_en = {
        "name": "LyaMusic",
        "searching": "<b><emoji document_id=5188311512791393083>🔎</emoji> Searching music...</b>",
        "no_results": "<b><emoji document_id=5210952531676504517>❌</emoji> Could not find the track, try entering the correct track name or track author.</b>",
        "loading": "<b><emoji document_id=5451732530048802485>⏳</emoji> Downloading track...</b>",
        "enter_name": "<b><emoji document_id=5210952531676504517>❌</emoji> Enter track name </b>"
    }

    async def searchmcmd(self, message):
        """{Название трека} - Поиск трека."""
        args = "/search " + utils.get_args_raw(message)
        if not args:
            await message.edit(self.strings("enter_name"))
            return

        await message.edit(self.strings("searching"))
        
        try:
            async with message.client.conversation("@LyaDownbot") as conv:
                await conv.send_message(args)
                while True:
                    response = await conv.get_response()
                    if "Не удалось найти трек" in response.text:
                        await message.edit(self.strings("no_results"))
                        return
                    
                    if "Загрузка трека" in response.text:
                        await message.edit(self.strings("loading"))

                    if response.media:
                        await message.client.send_file(message.chat_id, response.media)
                        await message.delete()
                        return

                    await asyncio.sleep(1)
                    updated_response = await message.client.get_messages(conv.chat_id, ids=response.id)
                    if updated_response.text != response.text and "Не удалось найти трек" in updated_response.text:
                        await message.edit(self.strings("no_results"))
                        return

        except Exception as e:
            await message.edit(self.strings("no_results"))