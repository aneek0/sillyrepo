import requests
from io import BytesIO
from pdf2image import convert_from_bytes
from hikkatl.types import Message
from .. import loader, utils

@loader.tds
class CovitPDFModule(loader.Module):
    """Модуль для скачивания PDF с сайта novkrp.ru и отправки его как изображения"""
    
    strings = {"name": "CovitPDF"}

    async def pdfcmd(self, message: Message):
        """Скачать PDF и отправить первую страницу как изображение"""
        await utils.answer(message, "<b>Скачивание и обработка PDF...</b>")
        
        try:
            # Скачиваем PDF-файл
            pdf_url = "https://www.novkrp.ru/data/covid_pit.pdf"
            response = requests.get(pdf_url)
            
            if response.status_code != 200:
                raise Exception("Не удалось скачать PDF")
            
            # Преобразуем PDF в изображения
            images = convert_from_bytes(response.content)
            if not images:
                raise Exception("PDF не содержит страниц")
            
            # Отправляем первую страницу как изображение без подписи
            with BytesIO() as output:
                images[0].save(output, format="JPEG")
                output.seek(0)
                await self._client.send_file(
                    message.peer_id,
                    output,
                    reply_to=message.reply_to_msg_id or message.id,
                )
            
            await message.delete()  # Удаляем исходное сообщение после отправки
        
        except Exception as e:
            await utils.answer(message, f"<b>Ошибка:</b> {str(e)}")