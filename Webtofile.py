import io
import re
import mimetypes
import requests
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class Web2fileMod(loader.Module):
    strings = {"name": "Web2file"}

    async def wtfcmd(self, message: Message):
        website = utils.get_args_raw(message)
        if not website and message.reply_to_msg_id:
            replied = await message.get_reply_message()
            website = self._extract_url(replied.text) if replied else None
        if not website:
            await utils.answer(message, "\U0001f6ab <b>Specify link</b>")
            return

        website = re.sub(r"<.*?>", "", website)
        if not website.startswith("http"):
            website = "http://" + website

        await message.delete()

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(website, stream=True, headers=headers, timeout=30)
            if resp.status_code != 200:
                await self._client.send_message(
                    message.chat_id,
                    f"\U0001f6ab <b>Error {resp.status_code}: {resp.reason}</b>",
                )
                return

            f = io.BytesIO()
            for chunk in resp.iter_content(1024):
                if chunk:
                    f.write(chunk)
            f.seek(0)

            cd = resp.headers.get("Content-Disposition", "")
            filename = None
            if cd:
                m = re.findall(r"filename\*=UTF-8''(.+)|filename=\"?([^\";]+)\"?", cd)
                if m:
                    filename = m[0][0] or m[0][1]
            if not filename:
                filename = website.split("/")[-1] or "file"
                if "." not in filename:
                    ext = mimetypes.guess_extension(resp.headers.get("Content-Type", "").split(";")[0]) or ""
                    filename += ext
            f.name = filename

        except requests.exceptions.RequestException as e:
            await self._client.send_message(
                message.chat_id, f"\U0001f6ab <b>Request error: {e}</b>"
            )
            return
        except Exception as e:
            await self._client.send_message(
                message.chat_id, f"\U0001f6ab <b>Unexpected error: {e}</b>"
            )
            return

        await self._client.send_file(
            message.chat_id,
            file=f,
            caption=f"\U0001f4e5 Downloaded from: <code>{website}</code>",
        )

    def _extract_url(self, text: str) -> str:
        m = re.search(r"(https?://[^\s]+)", text)
        return m.group(0) if m else None
