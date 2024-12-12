__version__ = (1, 0, 0)
import asyncio
import logging
from telethon.tl.types import DocumentAttributeFilename
from .. import loader, utils

fire = "🔥 "
warn = "🚨 "
wait = "🕒 "
done = "✅ "

class RenamerMod(loader.Module):
	"""Rename file name"""
	
	strings = {
	           "name": "Rename",
			   "no_reply": warn + "<b>Reply to file?</b>",
			   "no_name": fire + "<b>What's the name?</b>",
			   "wait": wait + "<b>Please, wait...</b>",
			   "oad": fire + "<b>Loading »»</b>",
			   "down": fire + "<b>Downloading »»</b>",
			   "done": done + "<b>Done</b>",
			   }
	
	strings_ru = {
			   "no_reply": warn + "<b>А ответ на файл?</b>",
			   "no_name": fire + "<b>Как назвать?</b>",
			   "wait": wait + "<b>Пожалуйста, подождите...</b>",
			   "load": fire + "<b>Загрузка »»</b>",
			   "down": fire + "<b>Скачивание »»</b>",
			   "done": done + "<b>Готов</b>",
			   }
	
	async def renamecmd(self, message):
		"""> rename [name.format]"""
        
		await message.edit(f"{self.strings('wait')}")
		reply = await message.get_reply_message()
		if not reply or not reply.file:
			await message.edit(self.strings["no_reply"])
			return
		name = utils.get_args_raw(message)
		if not name:
			await message.edit(self.strings["no_name"])
			return
		fn = reply.file.name
		if not fn:
			fn = ""
		fs = reply.file.size
		
		[await message.edit(f"<b>{self.strings('down')} {fn}</b>") if fs > 500000 else ...]
		file = await reply.download_media(bytes)
		[await message.edit(f"<b>{self.strings('load')}</b> <code>{name}</code>") if fs > 500000 else ...]
		await message.client.send_file(message.to_id, file, force_document=True, reply_to=reply, attributes=[DocumentAttributeFilename(file_name=name)], caption=f"{self.strings('done')} | <code>{name}</code>")
		await message.delete()
