from telethon.tl.functions.channels import GetAdminedPublicChannelsRequest
from telethon.tl.functions.messages import SendMessageRequest
from telethon.tl.types import InputPeerChannel, Message
from .. import loader, utils

@loader.tds
class ChannelSenderMod(loader.Module):
    """Send messages to all your channels"""

    strings = {"name": "ChannelSender"}

    async def chscmd(self, message: Message):
        """Send message to all your channels: .chs <message> or reply to a message"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if not args and not reply:
            await message.edit("<b>Usage:</b> .chs <message> or reply to a message")
            return

        # Если текст команды есть, то отправляем его, иначе отправляем текст сообщения, на которое был ответ
        text_to_send = args if args else reply.raw_text

        await message.edit("<b>Sending message to all channels...</b>")

        # Получаем все каналы, где пользователь администратор
        result = await message.client(GetAdminedPublicChannelsRequest())
        channels = result.chats

        sent_channels = []
        for channel in channels:
            try:
                # Отправляем сообщение в каждый канал
                await message.client(SendMessageRequest(
                    peer=InputPeerChannel(channel.id, channel.access_hash),
                    message=text_to_send
                ))
                # Добавляем канал в список успешных отправок
                sent_channels.append((channel.title, channel.username or channel.id))
            except Exception as e:
                await message.client.send_message(message.chat_id, f"Failed to send message to {channel.title}: {str(e)}")

        if sent_channels:
            # Создаем кликабельный список каналов
            channel_list = "\n".join(
                f"• <a href='https://t.me/{username}'>{title}</a>"
                for title, username in sent_channels
            )
            await message.edit(f"<b>Message sent to {len(sent_channels)} channels:</b>\n\n{channel_list}", parse_mode="HTML")
        else:
            await message.edit("<b>No messages were sent.</b>")