# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import os
from hikkatl.types import Message
from .. import loader, utils

@loader.tds
class RenamerModule(loader.Module):
    """Модуль для переименования файлов по реплаю"""

    strings = {"name": "Renamer"}

    async def renamecmd(self, message: Message):
        """Переименовать файл из реплая. Использование: .rename <новое_имя>"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "<b>Использование:</b> .rename <новое_имя>")
            return

        reply = await message.get_reply_message()
        if not reply or not reply.file:
            await utils.answer(message, "<b>Ответьте на сообщение с файлом.</b>")
            return

        new_name = args.strip()
        if "/" in new_name or "\\" in new_name:
            await utils.answer(message, "<b>Недопустимое имя файла!</b>")
            return

        # Загрузка файла
        file_path = await reply.download_media()
        if not file_path:
            await utils.answer(message, "<b>Ошибка при загрузке файла.</b>")
            return

        # Переименование файла
        renamed_path = os.path.join(os.path.dirname(file_path), new_name)
        try:
            os.rename(file_path, renamed_path)
        except Exception as e:
            await utils.answer(message, f"<b>Ошибка при переименовании файла:</b> {str(e)}")
            return

        # Отправка переименованного файла
        await self._client.send_file(
            message.chat_id,
            renamed_path,
            caption=f"<b>Файл переименован ✅</b>",
            reply_to=reply.id,
        )

        # Удаление временного файла
        os.remove(renamed_path)

        await message.delete()  # Удаляем исходное сообщение
