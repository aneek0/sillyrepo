from .. import loader, utils
from datetime import datetime, timedelta

class DeleteMessages(loader.Module):
    """Удаляет сообщения по времени, количеству, содержимому или с привязкой к ответу одномоментно.
    ОН ТОЧНО РАБОТАЕТ"""

    strings = {"name": "DeleteMessages"}

    async def client_ready(self, client, db):
        self.client = client

    async def delmestcmd(self, message):
        """Удаляет сообщения за период. Пример: .delmest 1d / 2h / 30m"""
        args = utils.get_args_raw(message)
        if not args:
            return

        try:
            duration, unit = int(args[:-1]), args[-1]
            delta = {
                "d": timedelta(days=duration),
                "h": timedelta(hours=duration),
                "m": timedelta(minutes=duration)
            }.get(unit)

            if not delta:
                return

            start_date = datetime.now() - delta
            messages_to_delete = []

            async for msg in self.client.iter_messages(message.chat_id, from_user="me"):
                if msg.date.replace(tzinfo=None) > start_date:
                    messages_to_delete.append(msg.id)

            if messages_to_delete:
                await self.client.delete_messages(message.chat_id, messages_to_delete)
        except ValueError:
            return

    async def delmescmd(self, message):
        """Удаляет X сообщений или все. Пример: .delmes 10 / .delmes all"""
        args = utils.get_args_raw(message)
        if not args:
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
        except ValueError:
            return

    async def delsocmd(self, message):
        """Удаляет сообщения по тексту. Пример: .delso текст"""
        args = utils.get_args_raw(message)
        if not args:
            return

        messages_to_delete = []
        async for msg in self.client.iter_messages(message.chat_id, search=args, from_user="me"):
            messages_to_delete.append(msg.id)

        if messages_to_delete:
            await self.client.delete_messages(message.chat_id, messages_to_delete)

    async def dpcmd(self, message):
        """Удаляет сообщение, на которое ответили, и все сообщения после него. Добавьте -m для удаления только ваших сообщений."""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if not reply:
            return

        only_mine = "-m" in args
        messages_to_delete = []

        async for msg in self.client.iter_messages(message.chat_id):
            if msg.id >= reply.id:
                if only_mine and msg.from_id != (await self.client.get_me()).id:
                    continue
                messages_to_delete.append(msg.id)

        if messages_to_delete:
            await self.client.delete_messages(message.chat_id, messages_to_delete)
            await message.delete()  # Удаляем командное сообщение
