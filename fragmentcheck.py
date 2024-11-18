import requests
from bs4 import BeautifulSoup
from .. import loader, utils

class Fragment(loader.Module):
    """Узнать сколько стоит юзер на Fragment.com"""
    
    strings = {"name": "Check Fragment"}
    
    @loader.command()
    async def ucheck(self, message):
        """Сколько стоит юзер на Fragment.com"""
        args = utils.get_args_raw(message)
        response = requests.get(f"https://fragment.com/username/{args}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            elements = soup.select(".table-cell-value.tm-value.icon-before.icon-ton")
        if elements:
            text = elements[0].text.strip()
            await utils.answer(message, f"<emoji document_id=5409029920787548613>📱</emoji> <b>Юзернейм найден!!</b>\n<emoji document_id=5418254819049621396>🖕</emoji> <b>Юзернейм:</b> <code>{args}</code>\n<emoji document_id=5409319277029245190>💵</emoji> <b>Стоит:</b> <code>{text}</code> TON")
        if not elements:
            await utils.answer(message, f"<emoji document_id=5406642649115414893>😡</emoji> <b>Юзернейм <code>{args}</code> не найден!!</b>")