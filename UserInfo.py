# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import requests
import asyncio
import os
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Message, Channel
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon import Button
from .. import loader, utils

def get_creation_date(user_id: int) -> str:
    url = "https://restore-access.indream.app/regdate"
    headers = {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": "Nicegram/92 CFNetwork/1390 Darwin/22.0.0",
        "x-api-key": "e758fb28-79be-4d1c-af6b-066633ded128",
        "accept-language": "en-US,en;q=0.9",
    }
    data = {"telegramId": user_id}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200 and "data" in response.json():
        return response.json()["data"]["date"]
    else:
        return "Ошибка получения данных"

@loader.tds
class UserInfoMod(loader.Module):
    """Получение информации о пользователе или канале Telegram, включая дату регистрации и данные из Фанстата"""

    strings = {
        "name": "UserInfo",
        "loading": "🕐 <b>Обработка данных...</b>",
        "not_chat": "🚫 <b>Это не чат!</b>",
        "unblock_bot": "❗ Разблокируйте @Funstatlol_bot для получения дополнительной информации.",
        "timeout": "⚠️ Время ожидания ответа от @Funstatlol_bot истекло.",
        "invalid_id": "❗ <b>Неверный ID!</b> Пожалуйста, проверьте правильность введенного ID.",
    }

    async def userinfocmd(self, message: Message):
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        await utils.answer(message, self.strings("loading"))
        if args.isdigit():
            user_or_channel_id = int(args)
        elif args:
            user_or_channel_id = args
        else:
            user_or_channel_id = reply.sender_id if reply else None
        
        if not user_or_channel_id:
            await utils.answer(message, "❗ Пожалуйста, укажите ID или @юзернейм.")
            return

        try:
            entity = await self._client.get_entity(user_or_channel_id)
        except Exception as e:
            await utils.answer(message, f"❗ Не удалось найти пользователя или канал: {e}")
            return

        if isinstance(entity, Channel):
            await self.process_channel_info(entity, message)
        else:
            await self.process_user_info(entity, message)

    async def process_user_info(self, user_ent, message):
        user = await self._client(GetFullUserRequest(user_ent.id))
        registration_date = get_creation_date(user_ent.id)
        funstat_info = await self.get_funstat_info(user_ent.id)

        user_info = (
            "<b>👤 Информация о пользователе:</b>\n\n"
            f"<b>Имя:</b> <code>{user_ent.first_name or '🚫'}</code>\n"
            f"<b>Фамилия:</b> <code>{user_ent.last_name or '🚫'}</code>\n"
            f"<b>Юзернейм:</b> @{user_ent.username or '🚫'}\n"
            f"<b>Описание:</b>\n{user.full_user.about or '🚫'}\n\n"
            f"<b>Дата регистрации:</b> <code>{registration_date}</code>\n"
            f"<b>Общие чаты:</b> <code>{user.full_user.common_chats_count}</code>\n"
            f"<b>ID:</b> <code>{user_ent.id}</code>\n"
        )

        if user_ent.username:
            user_info += f'<b><a href="tg://user?id={user_ent.id}">🌐 Вечная ссылка</a></b>\n\n'
        else:
            user_info += "Вечная ссылка отсутствует.\n\n"

        user_info += f"<b>📊 Информация из <a href='https://t.me/Funstatlol_bot'>Фанстата</a>:</b>\n{funstat_info}"

        photo = await self._client.download_profile_photo(user_ent.id)

        if photo:
            await self._client.send_file(
                message.chat_id,
                file=photo,
                caption=user_info,
                buttons=[
                    [Button.inline("🔄 Обновить данные", data=f"refresh:{user_ent.id}")]
                ]
            )

            try:
                os.remove(photo)
            except Exception as e:
                print(f"Ошибка при удалении аватара: {e}")

        else:
            await self._client.send_message(message.chat_id, user_info)

        await message.delete()

    async def process_channel_info(self, channel_ent, message):
        channel = await self._client(GetFullChannelRequest(channel_ent))
        description = channel.full_chat.about or "🚫"
        creation_date = get_creation_date(channel_ent.id)
        subscriber_count = channel.full_chat.participants_count

        channel_info = (
            "<b>📣 Информация о канале:</b>\n\n"
            f"<b>Название:</b> <code>{channel_ent.title}</code>\n"
            f"<b>Юзернейм:</b> @{channel_ent.username or '🚫'}\n"
            f"<b>Описание:</b>\n{description}\n\n"
            f"<b>Дата создания:</b> <code>{creation_date}</code>\n"
            f"<b>Количество подписчиков:</b> <code>{subscriber_count}</code>\n"
            f"<b>ID:</b> <code>{channel_ent.id}</code>\n"
        )

        if channel_ent.username:
            channel_info += f'<b><a href="https://t.me/{channel_ent.username}">Ссылка на канал</a></b>\n\n'
        else:
            channel_info += "Ссылка на канал отсутствует.\n\n"

        photo = await self._client.download_profile_photo(channel_ent.id)

        if photo:
            await self._client.send_file(
                message.chat_id,
                file=photo,
                caption=channel_info,
                buttons=[
                    [Button.inline("🔄 Обновить данные", data=f"refresh:{channel_ent.id}")]
                ]
            )

            try:
                os.remove(photo)
            except Exception as e:
                print(f"Ошибка при удалении аватара: {e}")

        else:
            await self._client.send_message(message.chat_id, channel_info)

        await message.delete()

    async def get_funstat_info(self, user_id: int) -> str:
        chat = "@Funstatlol_bot"
        attempts = 3
        for attempt in range(attempts):
            try:
                await self._client.send_message(chat, str(user_id))
                await asyncio.sleep(5)
                messages = await self._client.get_messages(chat, limit=5)
                for message in messages:
                    if f"👤 {user_id}" in message.text or str(user_id) in message.text:
                        lines = message.text.split("\n")
                        filtered_lines = [
                            line for line in lines if "ID:" not in line and "Это" not in line
                        ]
                        return "\n".join(filtered_lines)

                await asyncio.sleep(1)

            except YouBlockedUserError:
                return self.strings("unblock_bot")
            except Exception as e:
                return f"Ошибка при получении данных: {e}"

        return "⚠️ Не удалось получить окончательный ответ от @Funstatlol_bot"

