# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import mimetypes
import os
import requests
from .. import loader, utils

@loader.tds
class animetoolsMod(loader.Module):
    """FindAnime"""

    strings = {
        "name": "FindAnime",
        "no_results": "<emoji document_id=5210952531676504517>❌</emoji> Результатов не найдено!",
        "loading": "<emoji document_id=5213452215527677338>⏳</emoji> Загрузка ...",
        "error": "<emoji document_id=5215273032553078755>❎</emoji> Произошла ошибка, попробуйте снова",
        "reply": "<emoji document_id=5215273032553078755>❌</emoji> Нужно ответить на фото/видео или прикрепить его!",
        "findanime": "<emoji document_id=5215644719022874555>ℹ️</emoji> <b>Аниме:</b> <code>{}</code>\n<emoji document_id=6032602169360780718>🤨</emoji> <b>Похоже на:</b> <code>{}%</code>\n<emoji document_id=6334664298710697689>🍿</emoji> <b>Эпизод:</b> <code>{}</code>",
        "_cmd_doc_findanime": "Ищет по картинке что за аниме",
        "no_desc": "❌ Без описания!"    
    }


    @loader.command(alias="fa")
    async def findanimecmd(self, message):
        """Search by picture for what anime"""
        loading = await utils.answer(message, self.strings["loading"])
        reply_msg = await message.get_reply_message()
        msg = reply_msg or message
        media = msg.media
        if media:
            if msg.photo:
                filename = "photo.png"
            elif msg.video:
                filename = "video.mp4"
            elif msg.gif:
                filename = "gif.gif"
            else:
                filename = "photo.png"

            filename = await self.client.download_media(media, file=filename)
            typem, encoding = mimetypes.guess_type(filename)
            r = requests.post(
                "https://api.trace.moe/search",
                data=open(filename, "rb"),
                headers={"Content-Type": typem}
            ).json()

            res = r['result'][0]
            episode = res['episode']
            video = res['video']
            name = res['filename'].split('.')[0]
            simil = res['similarity']
            await loading.delete()
            await utils.answer_file(
                message,
                file=video,
                caption=self.strings["findanime"].format(name, simil*100, episode)
            )
            os.remove(filename)
        else:
            await utils.answer(message, self.strings['reply'])
