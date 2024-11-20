from hikka import loader, utils
import asyncio
from datetime import datetime, timedelta

@loader.tds
class ScheduledMessagesMod(loader.Module):
    """Отправка отложенных сообщений более простым и гибким способом."""
    strings = {"name": "ScheduledMessages"}

    async def client_ready(self, client, db):
        self.db = db
        self.client = client
        self.interval = 3600  # Интервал по умолчанию 1 час
        self.message_count = 10  # Количество сообщений по умолчанию

    async def settimecmd(self, message):
        """Указать интервал в минутах"""
        args = utils.get_args_raw(message)
        if not args.isdigit():
            await message.edit("Пожалуйста, укажите интервал в минутах используя числа нужные вам")
            return
        
        self.interval = int(args) * 60  # Преобразуем минуты в секунды
        await message.edit(f"Интервал сообщений установлен на {args} минут")

    async def setcountcmd(self, message):
        """Установить нужное количество сообщений"""
        args = utils.get_args_raw(message)
        if not args.isdigit():
            await message.edit("Пожалуйста, укажи количество сообщений")
            return
        
        self.message_count = int(args)
        await message.edit(f"Количество сообщений установлено на {args}.")

    async def settextcmd(self, message):
        """Укажите в формате <текст сообщения> [chat_id]"""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("Пожалуйста, укажи текст сообщения и, по желанию, chat_id")
            return

        # Разделяем строку на части
        parts = args.split(' ')
        
        # Убедимся, что последний элемент является числом (chat_id), если нет, то это чат текущий
        if parts[-1].isdigit():
            chat_id = int(parts[-1])
            text = ' '.join(parts[:-1])  # Текст сообщения - все, что до chat_id
        else:
            chat_id = message.chat.id  # Используем текущий чат, если chat_id не указан
            text = ' '.join(parts)  # Текст сообщения - всё

        if not text:
            await message.edit("Пожалуйста, укажи текст сообщения")
            return
        
        await message.delete()

        # Запланируем сообщения
        for i in range(self.message_count):
            send_time = datetime.now() + timedelta(seconds=self.interval * i)
            try:
                await self.client.send_message(chat_id, text, schedule=send_time)
            except Exception as e:
                await message.edit(f"Не удалось отправить сообщение в чат {chat_id}: {e}")
                return