# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

from .. import loader, utils

@loader.tds
class ValutatorMod(loader.Module):
    """Currency converter via @aneekocurrency_bot"""
    strings = {"name": "Valutator"}

    async def currcmd(self, message):
        """<amount> <from> <to> - Convert currency"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "<b>Usage: .curr 10usd")
            return

        message = await utils.answer(message, "<emoji document_id=5346192260029489215>💵</emoji> <b>Конвертирую...</b>")
        
        async with self._client.conversation("@aneekocurrency_bot") as conv:
            try:
                await conv.send_message(args)
                response = await conv.get_response()
                await utils.answer(message, response.text)
            except Exception as e:
                await utils.answer(message, f"<b>Error:</b> {str(e)}")