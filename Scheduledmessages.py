# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from hikka import loader, utils
import asyncio
from datetime import datetime, timedelta

@loader.tds
class ScheduledMessagesMod(loader.Module):
    """Отправка отложенных сообщений более простым и гибким способом."""
    strings = {"name": "ScheduledMessages"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "chats", [],  # Список ID чатов для отправки сообщений
                lambda: "Чаты для отправки отложенных сообщений",
                validator=loader.validators.Series(loader.validators.Integer())  # Проверка на список целых чисел
            ),
            loader.ConfigValue(
                "messages", [],  # Список фраз для отправки
                lambda: "Список фраз для отправки сообщений",
                validator=loader.validators.Series(loader.validators.String())  # Проверка на список строк
            ),
            loader.ConfigValue(
                "interval", 1440,  # Интервал в минутах по умолчанию (1 минута)
                lambda: "Интервал между отправками сообщений (в минутах)",
                validator=loader.validators.Integer()  # Проверка на целое число
            ),
            loader.ConfigValue(
                "message_count", 5,  # Количество сообщений по умолчанию
                lambda: "Количество отправляемых сообщений",
                validator=loader.validators.Integer()  # Проверка на целое число
            ),
        )

    async def client_ready(self, client, db):
        """Инициализация модуля"""
        self.client = client
        self.db = db
        self.interval = self.config["interval"]
        self.message_count = self.config["message_count"]

    @loader.command(ru_doc="[интервал] - Установить интервал для отправки сообщений в минутах.")
    async def settimecmd(self, message):
        """Указать интервал в минутах"""
        args = utils.get_args_raw(message)
        if not args.isdigit():
            await message.edit("Пожалуйста, укажите интервал в минутах, используя числа.")
            return

        interval = int(args)
        if interval < 1:
            await message.edit("Интервал должен быть хотя бы 1 минута.")
            return

        self.config["interval"] = interval
        await message.edit(f"Интервал сообщений установлен на {args} минут.")

    @loader.command(ru_doc="[количество] - Установить количество сообщений.")
    async def setcountcmd(self, message):
        """Установить нужное количество сообщений"""
        args = utils.get_args_raw(message)
        if not args.isdigit():
            await message.edit("Пожалуйста, укажите количество сообщений.")
            return

        message_count = int(args)
        if message_count < 1:
            await message.edit("Количество сообщений должно быть хотя бы 1.")
            return

        self.config["message_count"] = message_count
        await message.edit(f"Количество сообщений установлено на {args}.")

    @loader.command(ru_doc="[фразы] - Установить список фраз для отправки.")
    async def settextcmd(self, message):
        """Укажите фразы для отправки с отложенными сообщениями."""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("Пожалуйста, укажите хотя бы одну фразу для отправки.")
            return

        # Разделим фразы по запятой
        phrases = [phrase.strip() for phrase in args.split(',')]
        self.config["messages"] = phrases
        await message.edit(f"Фразы для отправки: {', '.join(phrases)}.")

    @loader.command(ru_doc="[чаты] - Добавить чаты для отправки сообщений.")
    async def addchatcmd(self, message):
        """Добавить чаты для отложенных сообщений."""
        chat_id_str = utils.get_args_raw(message)  # Получаем ID чата
        if not chat_id_str.isdigit():
            await message.edit("Пожалуйста, укажите корректный ID чата.")
            return
        
        chat_id = int(chat_id_str)
        chats = self.config["chats"]
        if chat_id not in chats:
            chats.append(chat_id)
            self.config["chats"] = chats  # Сохраняем новый список чатов в конфиг
            await message.edit(f"Чат с ID {chat_id} успешно добавлен.")
        else:
            await message.edit(f"Чат с ID {chat_id} уже добавлен.")

    async def send_scheduled_messages(self):
        """Отправить отложенные сообщения с интервалами"""
        messages = self.config["messages"]
        chats = self.config["chats"]
        
        # Если нет чатов или сообщений, выходим
        if not chats or not messages:
            return

        for chat_id in chats:
            for i in range(self.message_count):
                for message in messages:
                    send_time = datetime.now() + timedelta(minutes=self.interval * i)  # Изменили на минуты
                    try:
                        # Получаем сущность чата по ID
                        chat = await self.client.get_entity(chat_id)
                        # Отправляем сообщение в чат по расписанию
                        await self.client.send_message(chat, message, schedule=send_time)
                    except Exception as e:
                        await self.client.send_message(chat_id, f"Не удалось отправить сообщение: {e}")

    @loader.command(ru_doc="Запустить отложенную отправку сообщений.")
    async def startmessagescmd(self, message):
        """Запустить отложенную отправку сообщений."""
        await self.send_scheduled_messages()
        await message.edit("Отложенные сообщения были отправлены.")