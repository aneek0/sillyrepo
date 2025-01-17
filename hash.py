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
        "hash_result": "📄 <b>Хеш файла:</b>\n\n<code>MD5:</code> {}\n<code>SHA-1:</code> {}\n<code>SHA-256:</code> {}",
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

        # Скачиваем файл
        file_data = await reply.download_media(bytes)

        # Вычисляем хеши
        md5_hash = hashlib.md5(file_data).hexdigest()
        sha1_hash = hashlib.sha1(file_data).hexdigest()
        sha256_hash = hashlib.sha256(file_data).hexdigest()

        # Отправляем результат
        await utils.answer(
            message,
            self.strings("hash_result").format(md5_hash, sha1_hash, sha256_hash),
        )