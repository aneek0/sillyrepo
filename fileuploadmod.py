# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import os
from telethon import types
from .. import loader, utils

@loader.tds
class FileUploadMod(loader.Module):
    """Uploads files from the external storage"""
    strings = {"name": "FileUploadMod"}

    async def client_ready(self, client, db):
        self.client = client

    @loader.command()
    async def upload(self, message):
        """Upload a file from the external storage. Usage: .upload /path/to/file"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "<b>Please provide the file path.</b>")
            return
        
        file_path = args.strip()
        
        # Check if the file exists
        if not os.path.exists(file_path):
            await utils.answer(message, f"<b>File not found at {file_path}</b>")
            return

        try:
            # Upload the file to the chat
            await self.client.send_file(message.chat_id, file_path, caption=f"Uploaded file: {file_path}")
            await message.delete()  # Delete the command message after file upload
        except Exception as e:
            await utils.answer(message, f"<b>Error uploading the file:</b> {str(e)}")