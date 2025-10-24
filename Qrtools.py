# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import aiohttp
import qrcode
from io import BytesIO
from PIL import Image
from .. import loader, utils
from telethon.tl.types import DocumentAttributeFilename


@loader.tds
class QRtoolsMod(loader.Module):
    """QR код сканер и генератор"""
    strings = {"name": "QRtools"}

    @loader.owner
    async def readqrcmd(self, message):
        """.readqr <reply to image with QR code> - Сканирует QR код с изображения"""
        reply = await message.get_reply_message()
        
        if not reply or not reply.media:
            await utils.answer(message, "<b>❌ Ответьте на сообщение с изображением QR кода!</b>")
            return
            
        # Проверяем, что это изображение
        if not self._is_image(reply):
            await utils.answer(message, "<b>❌ Это не изображение!</b>")
            return
            
        try:
            # Скачиваем изображение
            file_data = await message.client.download_file(reply.media)
            
            # Создаем BytesIO объект для изображения
            image_buffer = BytesIO(file_data)
            image = Image.open(image_buffer)
            
            # Используем онлайн API для распознавания QR кода
            async with aiohttp.ClientSession() as session:
                # Подготавливаем файл для отправки
                image_buffer.seek(0)
                form_data = aiohttp.FormData()
                form_data.add_field('file', image_buffer, filename='qr.png', content_type='image/png')
                
                async with session.post('https://api.qrserver.com/v1/read-qr-code/', data=form_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result and len(result) > 0 and 'symbol' in result[0]:
                            qr_text = result[0]['symbol'][0]['data']
                            if qr_text:
                                await utils.answer(message, f"<b>📱 QR код содержит:</b>\n{qr_text}")
                            else:
                                await utils.answer(message, "<b>❌ Не удалось распознать QR код или он пустой!</b>")
                        else:
                            await utils.answer(message, "<b>❌ QR код не найден на изображении!</b>")
                    else:
                        await utils.answer(message, "<b>❌ Ошибка при распознавании QR кода!</b>")
                        
        except Exception as e:
            await utils.answer(message, f"<b>❌ Ошибка: {str(e)}</b>")

    @loader.owner
    async def makeqrcmd(self, message):
        """.makeqr <text> - Создает QR код из текста"""
        text = utils.get_args_raw(message)
        
        if not text:
            await utils.answer(message, "<b>❌ Укажите текст для создания QR кода!</b>")
            return
            
        try:
            # Создаем QR код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(text)
            qr.make(fit=True)
            
            # Создаем изображение
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Конвертируем в BytesIO
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            buffer.name = "qr_code.png"
            
            # Отправляем как изображение
            await message.delete()
            await message.client.send_file(
                message.to_id, 
                buffer, 
                caption=f"<b>📱 QR код для:</b> {text}",
                force_document=False
            )
            
        except Exception as e:
            await utils.answer(message, f"<b>❌ Ошибка при создании QR кода: {str(e)}</b>")

    def _is_image(self, message):
        """Проверяет, является ли сообщение изображением"""
        if not message or not message.media:
            return False
            
        if message.photo:
            return True
            
        if message.document:
            # Проверяем, что это не анимированный стикер
            if DocumentAttributeFilename(file_name='AnimatedSticker.tgs') in message.media.document.attributes:
                return False
            # Проверяем, что это не видео/аудио/гиф
            if message.gif or message.video or message.audio or message.voice:
                return False
            return True
            
        return False
