# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import hashlib
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class HashMod(loader.Module):
    """Модуль для вычисления хеша файла"""

    strings = {
        "name": "FileHash",
        "no_reply": "🚫 <b>Ответьте на сообщение с файлом</b>",
        "no_file": "🚫 <b>В сообщении нет файла</b>",
        "hash_result": "📄 <b>Хеш файла:</b>\n\nMD5: <code>{}</code>\nSHA-1: <code>{}</code>\nSHA-256: <code>{}</code>",
    }

    strings_ru = {
        "_cmd_doc_hash": "Вычислить хеш файла (MD5, SHA-1, SHA-256)",
    }

    async def hashcmd(self, message: Message):
        """Вычислить хеш файла"""
        reply = await message.get_reply_message()

        if not reply or not reply.file:
            await utils.answer(message, self.strings("no_reply"))
            return

        file = reply.file
        if not file.size:
            await utils.answer(message, self.strings("no_file"))
            return

        file_data = await reply.download_media(bytes)

        md5_hash = hashlib.md5(file_data).hexdigest()
        sha1_hash = hashlib.sha1(file_data).hexdigest()
        sha256_hash = hashlib.sha256(file_data).hexdigest()

        await utils.answer(
            message,
            self.strings("hash_result").format(md5_hash, sha1_hash, sha256_hash),
        )