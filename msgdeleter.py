from .. import loader, utils
from datetime import datetime, timedelta

class DeleteMessages(loader.Module):
    """Удаляет сообщения по времени, количеству, содержимому или с привязкой к ответу одномоментно."""

    strings = {"name": "DeleteMessages"}

    async def client_ready(self, client, db):
        self.client = client

    async def delmestcmd(self, message):
        """Удаляет сообщения за период. Пример: .delmest 1d / 2h / 30m"""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("⚠️ Укажите период (например, 1d, 2h, 30m).")
            return

        try:
            duration, unit = int(args[:-1]), args[-1]
            delta = {
                "d": timedelta(days=duration),
                "h": timedelta(hours=duration),
                "m": timedelta(minutes=duration)
            }.get(unit)

            if not delta:
                await message.edit("⚠️ Неверный формат. Используйте d (дни), h (часы), m (минуты).")
                return

            start_date = datetime.now() - delta
            messages_to_delete = []

            async for msg in self.client.iter_messages(message.chat_id, from_user="me"):
                if msg.date.replace(tzinfo=None) > start_date:
                    messages_to_delete.append(msg.id)

            if messages_to_delete:
                await self.client.delete_messages(message.chat_id, messages_to_delete)
                await message.edit(f"✅ Удалено {len(messages_to_delete)} сообщений за последние {duration}{unit}.")
            else:
                await message.edit("⚠️ Сообщения для удаления не найдены.")
        except ValueError:
            await message.edit("⚠️ Неверный формат. Пример: .delmest 1d / 2h / 30m.")

    async def delmescmd(self, message):
        """Удаляет X сообщений или все. Пример: .delmes 10 / .delmes all"""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("⚠️ Укажите количество сообщений или 'all'.")
            return

        messages_to_delete = []
        try:
            if args.lower() == "all":
                async for msg in self.client.iter_messages(message.chat_id, from_user="me"):
                    messages_to_delete.append(msg.id)
            else:
                limit = int(args)
                async for msg in self.client.iter_messages(message.chat_id, from_user="me"):
                    if len(messages_to_delete) >= limit:
                        break
                    messages_to_delete.append(msg.id)

            if messages_to_delete:
                await self.client.delete_messages(message.chat_id, messages_to_delete)
                await message.edit(f"✅ Удалено {len(messages_to_delete)} сообщений.")
            else:
                await message.edit("⚠️ Сообщения для удаления не найдены.")
        except ValueError:
            await message.edit("⚠️ Используйте .delmes {X} или .delmes all.")

    async def delsocmd(self, message):
        """Удаляет сообщения по тексту. Пример: .delso текст"""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("⚠️ Укажите текст для поиска сообщений.")
            return

        messages_to_delete = []
        async for msg in self.client.iter_messages(message.chat_id, search=args, from_user="me"):
            messages_to_delete.append(msg.id)

        if messages_to_delete:
            await self.client.delete_messages(message.chat_id, messages_to_delete)
            await message.edit(f"✅ Удалено {len(messages_to_delete)} сообщений с текстом: {args}.")
        else:
            await message.edit("⚠️ Сообщения для удаления не найдены.")

    async def dpcmd(self, message):
        """Удаляет сообщение, на которое ответили, и все сообщения после него."""
        reply = await message.get_reply_message()
        if not reply:
            await message.edit("⚠️ Ответьте на сообщение, чтобы использовать эту команду.")
            return

        messages_to_delete = []
        async for msg in self.client.iter_messages(message.chat_id):
            if msg.id >= reply.id:
                messages_to_delete.append(msg.id)

        if messages_to_delete:
            await self.client.delete_messages(message.chat_id, messages_to_delete)
            await message.delete()  # Удаляем командное сообщение без редактирования
        else:
            await message.edit("⚠️ Сообщения для удаления не найдены.")
