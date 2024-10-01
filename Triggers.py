import uuid
import asyncio
import logging
import json

from .. import loader, utils
from hikkatl.tl.types import Message

from cachetools import TTLCache


@loader.tds
class Triggers(loader.Module):
    """Triggers watches chat messages and can do anything, reply to a message with a given text, delete a message, execute any userbot command. Overall, a very cool module"""
    
    strings = {
        "name": "Triggers",
        "_cfg_status": "module working or not",
        "_cfg_allow_invoke": "can triggers run ANY userbot commands?",
        "_cfg_throttle_time": "cooldown between trigger executions",
        "no_reply": "❌ No reply!",
        "no_args": "❌ No args!",
        "text_add": (
            "✅ <b>Trigger successfully added</b>\n"
            "<i>id:</i> <code>{id}</code>"
        ),
        "empty": "🫗 Empty\n",
        "text_all": (
            "💬 <b>Your triggers:</b>\n"
            "{triggers}\n"
            "<i>in {chats} chats</i>"
        ),
        "chat_added": "⚡️ <b>Chat {chat} successfully added</b>",
        "chat_removed": "‼️ <b>Chat {chat} successfully removed</b>",
        "success": "✅ <b>Success</b>",
        "not_found": "❌ <b>Trigger not found!</b>",
        "not_valid": "❌ <b>Trigger is not valid!</b>",
        "error": "❌ <b>Unexpected error: {e}</b>"
    }
    
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "status",
                False,
                lambda: self.strings("_cfg_status"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "allow_invoke",
                False,
                lambda: self.strings("_cfg_allow_invoke"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "throttle_time",
                1.0,
                lambda: self.strings("_cfg_throttle_time"),
                validator=loader.validators.Float(minimum=0)
            ),
        )
        
        self.cache = TTLCache(maxsize=10_000, ttl=float(self.config["throttle_time"]))

    @loader.command(ru_doc="[текст, на который будет тригеррится модуль] <реплай на текст ответа> - Добавить базовый триггер", alias="tbaseadd")
    async def triggeraddbase(self, message: Message):
        """[text that the module will trigger on] <reply on the response text> - Add base trigger"""
        triggers = self.get("triggers", [])
        
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_args"))
            return
        
        reply = await message.get_reply_message()
        if not reply or not reply.text:
            await utils.answer(message, self.strings("no_reply"))
            return
        
        trigger = {
            "m": args,
            "id": str(uuid.uuid4())[:5],
            "action": {
                "type": "answer",
                "text": reply.text
            },
            "delay": 0
        }
        triggers.append(trigger)
        self.set("triggers", triggers)
        
        text = self.strings("text_add").format(id=trigger["id"])
        
        await utils.answer(message, text)

    @loader.command(ru_doc="[триггер] - Добавить триггер из сырых данных", alias="tadd")
    async def triggeradd(self, message: Message):
        """[trigger] - Add a trigger from raw data"""
        triggers = self.get("triggers", [])
        
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_args"))
            return
        
        trigger = json.loads(args)
        if not isinstance(trigger, dict) or not trigger["m"] or not trigger["action"]:
            return
        
        trigger["id"] = str(uuid.uuid4())[:5]
        if not trigger.get("delay") or trigger["delay"] < 0:
            trigger["delay"] = 0
        
        triggers.append(trigger)
        self.set("triggers", triggers)
        
        text = self.strings("text_add").format(id=trigger["id"])
        await utils.answer(message, text)

    @loader.command(ru_doc="Посмотреть все триггеры")
    async def triggers(self, message: Message):
        """View all triggers"""
        triggers = self.get("triggers", [])
        t = ""
        
        if not triggers:
            t = self.strings("empty")
        else:
            for trigger in triggers:
                t += f"  • {trigger['m']} {trigger['id']} action={trigger['action']['type']};\n"
        
        text = self.strings("text_all").format(
            triggers=t,
            chats=len(self.get("chats", []))
        )
        await utils.answer(message, text)

    @loader.command(ru_doc="Добавить чат, где будут работать триггеры")
    async def triggerchat(self, message: Message):
        """Add chat, where triggers will work"""
        chats = self.get("chats", [])
        chat_id = message.chat.id
        flag = False
        
        if chat_id not in chats:
            chats.append(chat_id)
            flag = True
        else:
            chats.remove(chat_id)
        
        self.set("chats", chats)
        
        text = (
            self.strings("chat_added").format(chat=chat_id)
            if flag
            else self.strings("chat_removed").format(chat=chat_id)
        )
        await utils.answer(message, text)

    @loader.command(ru_doc="[айди триггера] - Удалить триггер")
    async def triggerdel(self, message: Message):
        """[trigger's id] - Delete trigger"""
        args = utils.get_args_raw(message).split()
        if not args:
            await utils.answer(message, self.strings("no_args"))
            return
        
        triggers = self.get("triggers", [])
        for trigger in triggers:
            if trigger["id"] == args[0]:
                triggers.remove(trigger)
                self.set("triggers", triggers)
                await utils.answer(message, self.strings("success"))
                return
            
        await utils.answer(message, self.strings("not_found"))

    @loader.watcher()
    async def triggers_watcher(self, message: Message):
        """Watch for trigger events"""
        if not self.config["status"]:
            return
        
        if not message.text:
            return
        
        if not getattr(message, "chat") or (getattr(message, "chat") and message.chat.id not in self.get("chats", [])):
            return

    @loader.watcher()
    async def triggers_watcher(self, message: Message):
    """Watch for trigger events"""
    if not self.config["status"]:
        return
    
    if not message.text:
        return
    
    if not getattr(message, "chat") or (getattr(message, "chat") and message.chat.id not in self.get("chats", [])):
        return
    
    triggers = self.get("triggers", [])
    if not triggers:
        return
    
    t = []
    for trigger in triggers:
        if trigger.get("filters") and trigger["filters"].get("chats", []) != [] and message.chat.id not in trigger["filters"].get("chats", []):
            continue
        if trigger.get("filters") and trigger["filters"].get("from_users", []) != [] and message.from_id not in trigger["filters"].get("from_users", []):
            continue
        
        if trigger.get("filters") and trigger["filters"].get("ignorecase") is True:
            message.text = message.text.lower()
            
        if message.text == trigger["m"]:
            t.append(trigger)
            continue
            
        if trigger.get("filters") and trigger["filters"].get("contains", False) is True and trigger["m"] in message.text:
            t.append(trigger)
    
    for trigger in t:
        if trigger["id"] in self.cache:
            continue
        else:  # <-- Важно, этот блок "else" теперь правильно выровнен
            self.cache[trigger["id"]] = None

        action_type = trigger["action"]["type"]
        if trigger["delay"] != 0:
            await asyncio.sleep(trigger["delay"])
        
        if action_type == "answer":
            await message.reply(trigger["action"]["text"].format(text=message.text))
        elif action_type == "delete":
            await message.delete()
        elif action_type == "invoke":
            if self.config["allow_invoke"]:
                await self.invoke(
                    trigger["action"].get("command"),
                    trigger["action"].get("args", ""),
                    message=message
		)
		    
