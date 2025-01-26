# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from telethon import functions
from telethon.tl.types import Channel

from .. import loader, utils


@loader.tds
class MyUsernames(loader.Module):
    """The usernames I own"""

    strings = {"name": "My Usernames"}

    @loader.command()
    async def myusern(self, message):
        """A list of usernames that were created by me"""
        result = await self.client(functions.channels.GetAdminedPublicChannelsRequest())
        output_str = "• "
        for channel_obj in result.chats:
            if isinstance(channel_obj, Channel) and channel_obj.username is not None:
                output_str += (
                    f"<code>{channel_obj.title}</code> |"
                    f" <b>@{channel_obj.username}</b>\n• "
                )
        await utils.answer(
            message, f"<b>💼 List usernames reserved by me</b>\n\n{output_str[:-3]}"
        )
