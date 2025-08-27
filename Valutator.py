# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import asyncio
from telethon import events
from telethon.errors.rpcerrorlist import YouBlockedUserError

from .. import loader, utils

class ValutatorMod(loader.Module):
    """Работает с помощью бота @aneekocurrency_bot"""
    strings = {"name": "Valutator"}

    async def currcmd(self, message):
        """.curr <кол-во> <валюта>
        Конвертирует валюты
        Пример: '.curr 5000 рублей/руб/rub/RUB'
        """
        state = utils.get_args_raw(message)
        chat = "@aneekocurrency_bot"
        
        # Отправляем временное сообщение о том, что мы работаем
        temp_msg = await message.respond("<emoji document_id=5346192260029489215>💵</emoji> <b>Конвертирую...</b>")
        
        try:
            # Отправляем сообщение боту
            bot_send_message = await message.client.send_message(chat, format(state))
            
            # Ждём ответа от бота (максимум 30 секунд)
            async def wait_for_response():
                try:
                    async for event in message.client.iter_messages(chat, limit=1, reverse=True):
                        if event.id > bot_send_message.id:
                            return event
                    
                    # Если не нашли сообщение выше, ждём новое
                    async for event in message.client.iter_messages(chat, limit=1):
                        if event.id > bot_send_message.id:
                            return event
                    
                    return None
                except Exception:
                    return None
            
            # Ждём ответа с таймаутом
            try:
                bot_response = await asyncio.wait_for(wait_for_response(), timeout=30.0)
                if bot_response:
                    # Удаляем временное сообщение
                    await temp_msg.delete()
                    # Удаляем сообщение с командой
                    await message.delete()
                    # Отправляем новое сообщение с ответом от бота
                    await message.respond(bot_response.text)
                else:
                    # Удаляем временное сообщение
                    await temp_msg.delete()
                    # Удаляем сообщение с командой
                    await message.delete()
                    # Отправляем сообщение об ошибке
                    await message.respond("<b>Не удалось получить ответ от бота</b>")
            except asyncio.TimeoutError:
                # Удаляем временное сообщение
                await temp_msg.delete()
                # Удаляем сообщение с командой
                await message.delete()
                # Отправляем сообщение о таймауте
                await message.respond("<b>Таймаут ожидания ответа от бота</b>")
                
        except YouBlockedUserError:
            # Удаляем временное сообщение
            await temp_msg.delete()
            # Удаляем сообщение с командой
            await message.delete()
            # Отправляем сообщение об ошибке блокировки
            await message.respond("<b>Разблокируй</b> " + chat)
            return
        except Exception as e:
            # Удаляем временное сообщение
            await temp_msg.delete()
            # Удаляем сообщение с командой
            await message.delete()
            # Отправляем сообщение об ошибке
            await message.respond(f"<b>Ошибка:</b> {str(e)}")