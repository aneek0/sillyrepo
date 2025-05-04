import re
import asyncio
from telethon import events
from telethon.errors.rpcerrorlist import YouBlockedUserError
from .. import loader, utils

chat = "@projectaltair_bot"

class TTDownloadMod(loader.Module):
    strings = {"name": "TTDownloadMod"}

    async def client_ready(self, client, db):
        self.db = db

    async def ttdcmd(self, message):
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, "Please provide a TikTok link.")

        await utils.answer(message, "Downloading...")
        try:
            async with message.client.conversation(chat) as conv:
                response = conv.wait_event(
                    events.NewMessage(incoming=True, from_users=await message.client.get_peer_id(chat))
                )
                await message.client.send_message(chat, args)
                bot_response = await response

                if bot_response.media:
                    await message.client.forward_messages(message.to_id, bot_response.id, chat)
                else:
                    await utils.answer(message, "Бот не прислал медиа.")
        except YouBlockedUserError:
            await utils.answer(message, f"<b>Разблокируй</b> {chat}")

    async def ttacceptcmd(self, message):
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        users_list = self.db.get("TTsaveMod", "users", [])

        if args == "-l":
            if not users_list:
                return await utils.answer(message, "Список пуст.")
            return await utils.answer(
                message,
                "• " + "\n• ".join([f"<code>{i}</code>" for i in users_list]),
            )

        try:
            user = message.chat_id if not args and not reply else reply.sender_id if not args else int(args)
        except:
            return await utils.answer(message, "Неверно введён ID.")
        if user in users_list:
            users_list.remove(user)
            await utils.answer(message, f"ID <code>{user}</code> исключен.")
        else:
            users_list.append(user)
            await utils.answer(message, f"ID <code>{user}</code> добавлен.")
        self.db.set("TTsaveMod", "users", users_list)

    async def watcher(self, message):
        try:
            users = self.db.get("TTsaveMod", "users", [])
            if message.chat_id not in users:
                return

            links = re.findall(
                r"((?:https?://)?v[mt]\.tiktok\.com/[A-Za-z0-9_]+/?)", message.raw_text
            )
            if not links:
                return

            async with message.client.conversation(chat) as conv:
                for link in links:
                    await utils.answer(message, f"Отправляю ссылку в бот {chat}: {link}")
                    response = conv.wait_event(
                        events.NewMessage(incoming=True, from_users=await message.client.get_peer_id(chat))
                    )
                    await conv.send_message(link)
                    bot_response = await response

                    if bot_response.media:
                        await message.client.forward_messages(message.chat_id, bot_response.id, chat)
        except Exception as e:
            await utils.answer(message, f"Произошла ошибка: {e}")