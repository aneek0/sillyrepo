# meta developer: @aneek0
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils

class DaResponder(loader.Module):
    """Отвечает на "Da" или "da" с "Pizda" или "pizda"."""

    strings = {"name": "DaResponder"}

    async def client_ready(self, client, db):
        self.db = db

    async def dacmd(self, message):
        """.da - Добавить чат/личные сообщения в базу.
        .da -l - Показать список чатов в базе."""
        args = utils.get_args_raw(message)
        users_list = self.db.get("DaResponder", "users", [])

        if args == "-l":
            if len(users_list) == 0:
                return await utils.answer(message, "Список пуст.")
            return await utils.answer(message, "• " + "\n• ".join([str(i) for i in users_list]))

        user_id = message.chat_id

        if user_id in users_list:
            users_list.remove(user_id)
            await utils.answer(message, f"Ид {user_id} исключен.")
        else:
            users_list.append(user_id)
            await utils.answer(message, f"Ид {user_id} добавлен.")
        
        self.db.set("DaResponder", "users", users_list)

    async def watcher(self, message):
        users_list = self.db.get("DaResponder", "users", [])
        
        if message.chat_id not in users_list:
            return
        
        if message.text.lower() == "da":
            await message.reply("Pizda" if message.text == "Da" else "pizda")
