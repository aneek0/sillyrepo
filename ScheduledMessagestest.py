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
        """Укажите в формате <текст сообщения> [chat_username]"""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("Пожалуйста, укажи текст сообщения и, по желанию, username чата")
            return

        parts = args.split(' ')
        text = ' '.join(parts[:-1]) if parts[-1].startswith('@') else ' '.join(parts)
        chat_username = parts[-1] if parts[-1].startswith('@') else None

        if not text:
            await message.edit("Пожалуйста, укажи текст сообщения")
            return

        # Удаляем сообщение команды
        await message.delete()

        # Определяем чат
        try:
            if chat_username:
                entity = await self.client.get_entity(chat_username)
            else:
                entity = await self.client.get_input_entity(message.chat_id)
        except Exception as e:
            await message.respond(f"Ошибка при получении чата: {e}")
            return

        # Запланируем сообщения
        for i in range(self.message_count):
            send_time = datetime.now() + timedelta(seconds=self.interval * i)
            try:
                await self.client.send_message(entity, text, schedule=send_time)
            except Exception as e:
                await message.respond(f"Не удалось отправить сообщение в чат {chat_username or message.chat_id}: {e}")
                return
