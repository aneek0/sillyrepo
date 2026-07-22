# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils

@loader.tds
class FileUploadMod(loader.Module):
    """Uploads files from the external storage"""
    strings = {"name": "FileUploadMod"}

    @loader.command()
    async def upload(self, message):
        """Upload a file from the external storage. Usage: .upload /path/to/file"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "<b>Please provide the file path.</b>")
            return

        try:
            await self.client.send_file(message.chat_id, args.strip(), caption=f"Uploaded file: {args.strip()}")
            await message.delete()
        except Exception as e:
            await utils.answer(message, f"<b>Error uploading the file:</b> {str(e)}")