# meta developer: @EPEMEN

import io
import logging
import os
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageOps
from telethon.tl.types import DocumentAttributeFilename

from .. import loader, utils

logger = logging.getLogger(__name__)


def register(cb):
    cb(CirclesMod())


@loader.tds
class CirclesMod(loader.Module):
    """Делает кружочки из всего

Переделан под ffmpeg вместо moviepy"""

    strings = {"name": "Circles"}

    def __init__(self):
        self.name = self.strings["name"]

    async def client_ready(self, client, db):
        self.client = client

    @loader.sudo
    async def roundcmd(self, message):
        """ <Ответом на картинку/стикер или видео/ГИФ-ку>"""
        reply = None
        if message.is_reply:
            reply = await message.get_reply_message()
            data = await check_media(reply)
            if isinstance(data, bool):
                await utils.answer(
                    message, "<b>Ответь на картинку/стикер или видео/ГИФ-ку!</b>"
                )
                return
        else:
            await utils.answer(message, "<b>Ответь на картинку/стикер или видео/ГИФ-ку!</b>")
            return
        data, type = data
        if type == "img":
            await message.edit("📷 <b>Обработка фотки...</b>")
            img = io.BytesIO()
            bytes = await message.client.download_file(data, img)
            im = Image.open(img)
            w, h = im.size
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            img.paste(im, (0, 0))
            m = min(w, h)
            img = img.crop(((w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2))
            w, h = img.size
            mask = Image.new("L", (w, h), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((10, 10, w - 10, h - 10), fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(2))
            img = ImageOps.fit(img, (w, h))
            img.putalpha(mask)
            im = io.BytesIO()
            im.name = "img.webp"
            img.save(im)
            im.seek(0)
            await message.client.send_file(message.to_id, im, reply_to=reply)
        else:
            await message.edit("🎥 <b>Обработка видео...</b>")
            await message.client.download_file(data, "video.mp4")

            # Получение размеров видео
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                 'stream=width,height', '-of', 'csv=s=x:p=0', 'video.mp4'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            w, h = map(int, result.stdout.decode().strip().split('x'))
            m = min(w, h)
            box = [(w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2]

            # Обрезка видео с помощью ffmpeg
            crop_filter = f"crop={box[2] - box[0]}:{box[3] - box[1]}:{box[0]}:{box[1]}"
            subprocess.run(
                ['ffmpeg', '-i', 'video.mp4', '-vf', crop_filter, '-codec:v', 'libx264', 
                 '-preset', 'fast', '-tune', 'stillimage', '-pix_fmt', 'yuv420p',
                 '-movflags', '+faststart', '-max_muxing_queue_size', '1024', '-y', 'result.mp4']
            )

            # Преобразование в видеозапись с круглой маской
            subprocess.run(
                ['ffmpeg', '-i', 'result.mp4', '-vf', 
                 'format=yuv420p,scale=320:320,setsar=1,mpdecimate,setpts=N/FRAME_RATE/TB', 
                 '-c:v', 'libx264', '-preset', 'fast', '-y', 'video_note.mp4']
            )

            await message.edit("📼 <b>Загрузка видео...</b>")
            await message.client.send_file(
                message.to_id, "video_note.mp4", video_note=True, reply_to=reply
            )
            os.remove("video.mp4")
            os.remove("result.mp4")
            os.remove("video_note.mp4")
        await message.delete()


async def check_media(reply):
    type = "img"
    if reply and reply.media:
        if reply.photo:
            data = reply.photo
        elif reply.document:
            if (
                DocumentAttributeFilename(file_name="AnimatedSticker.tgs")
                in reply.media.document.attributes
            ):
                return False
            if reply.gif or reply.video:
                type = "vid"
            if reply.audio or reply.voice:
                return False
            data = reply.media.document
        else:
            return False
    else:
        return False
    if not data or data is None:
        return False
    else:
        return (data, type)