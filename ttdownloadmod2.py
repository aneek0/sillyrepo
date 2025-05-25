import re
import asyncio
from telethon import events
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon.tl.types import MessageMediaDocument
from .. import loader, utils

chat = "@uasaverbot"

class TTDownloadMod(loader.Module):
    strings = {"name": "TTDownloadMod"}

    async def client_ready(self, client, db):
        self.db = db

    async def ttdcmd(self, message):
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, "Please provide a TikTok link.")

        await utils.answer(message, "Downloading...")

        media_messages = []
        audio_received = asyncio.Event()
        peer_id = await message.client.get_peer_id(chat)

        async def handler(event):
            if event.message.sender_id == peer_id and event.message.media:
                media_messages.append(event.message)
                if (isinstance(event.message.media, MessageMediaDocument)
                    and event.message.media.document
                    and "audio" in event.message.media.document.mime_type):
                    audio_received.set()

        message.client.add_event_handler(handler, events.NewMessage(incoming=True, from_users=peer_id))

        try:
            await message.client.send_message(chat, args)

            has_video = any(
                isinstance(m.media, MessageMediaDocument)
                and m.media.document
                and "video" in m.media.document.mime_type
                for m in media_messages
            )

            if has_video:
                await message.client.forward_messages(
                    message.to_id,
                    [m.id for m in media_messages if m.media],
                    chat,
                )
            else:
                try:
                    await asyncio.wait_for(audio_received.wait(), timeout=15)
                except asyncio.TimeoutError:
                    pass

                if media_messages:
                    await message.client.forward_messages(
                        message.to_id,
                        [m.id for m in media_messages if m.media],
                        chat,
                    )
                else:
                    await utils.answer(message, "Бот не прислал медиа.")
        except YouBlockedUserError:
            await utils.answer(message, f"<b>Разблокируй</b> {chat}")
        except Exception as e:
            await utils.answer(message, f"Ошибка: {e}")
        finally:
            message.client.remove_event_handler(handler, events.NewMessage(incoming=True, from_users=peer_id))

    async def ttacceptcmd(self, message):
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        users_list = self.db.get("TTsaveMod", "users", [])

        if args == "-l":
            if not users_list:
                return await utils.answer(message, "Список пуст.")
            return await utils.answer(message, "• " + "\n• ".join([f"<code>{i}</code>" for i in users_list]))

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

            links = re.findall(r"((?:https?://)?v[mt]\.tiktok\.com/[A-Za-z0-9_]+/?)", message.raw_text)
            if not links:
                return

            peer_id = await message.client.get_peer_id(chat)

            for link in links:
                await utils.answer(message, f"Отправляю ссылку в бот {chat}: {link}")
                media_messages = []
                audio_received = asyncio.Event()

                async def handler(event):
                    if event.message.sender_id == peer_id and event.message.media:
                        media_messages.append(event.message)
                        if (isinstance(event.message.media, MessageMediaDocument)
                            and event.message.media.document
                            and "audio" in event.message.media.document.mime_type):
                            audio_received.set()

                message.client.add_event_handler(handler, events.NewMessage(incoming=True, from_users=peer_id))

                try:
                    await message.client.send_message(chat, link)

                    has_video = any(
                        isinstance(m.media, MessageMediaDocument)
                        and m.media.document
                        and "video" in m.media.document.mime_type
                        for m in media_messages
                    )

                    if has_video:
                        await message.client.forward_messages(
                            message.chat_id,
                            [m.id for m in media_messages if m.media],
                            chat,
                        )
                    else:
                        try:
                            await asyncio.wait_for(audio_received.wait(), timeout=15)
                        except asyncio.TimeoutError:
                            pass

                        if media_messages:
                            await message.client.forward_messages(
                                message.chat_id,
                                [m.id for m in media_messages if m.media],
                                chat,
                            )
                finally:
                    message.client.remove_event_handler(handler, events.NewMessage(incoming=True, from_users=peer_id))

        except Exception as e:
            await utils.answer(message, f"Произошла ошибка: {e}")