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
            bot_response = None
            response_received = asyncio.Event()
            chat_entity = await message.client.get_entity(chat)
            my_id = (await message.client.get_me()).id
            
            async def message_handler(event):
                nonlocal bot_response
                if (event.chat_id == chat_entity.id and 
                    event.sender_id != my_id and
                    event.id > bot_send_message.id and
                    not response_received.is_set()):
                    bot_response = event
                    response_received.set()
            
            # Регистрируем обработчик событий
            message.client.add_event_handler(message_handler, events.NewMessage)
            
            try:
                # Ждём ответа с таймаутом
                await asyncio.wait_for(response_received.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                pass
            finally:
                # Удаляем обработчик событий
                message.client.remove_event_handler(message_handler, events.NewMessage)
            
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