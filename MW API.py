from .. import loader, utils
from telethon.tl.types import Message
from ..inline.types import InlineCall
import aiohttp
import asyncio
import time
from io import BytesIO
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError
import requests

@loader.tds
class MW_APIMod(loader.Module):
    """🤖 Продвинутый модуль для работы с различными AI моделями"""

    strings = {
        "name": "MW API",
        "processing": "🤔 <b>Обрабатываю запрос...</b>",
        "response": "🤖 <b>Ответ от {}:</b>\n\n{}\n\n⏱ Время: {:.2f}с\n📊 Модель: {}\n🔧 API: MW",
        "image_response": "🖼️ <b>Сгенерировано за {:.2f} секунд</b>\n📊 Модель: {}\n🔗 Ссылка на изображение:{}",
        "error": "🚫 <b>Произошла ошибка при обработке запроса</b>",
        "no_args": "❌ <b>Укажите запрос!</b>",
        "settings_header": "⚙️ <b>Настройки MW API</b>\n\n📝 <b>Текущая модель:</b> <code>{}</code>",
        "model_changed": "✅ <b>Модель изменена на:</b> <code>{}</code>",
        "select_model": "🔄 <b>Выберите модель AI:</b>",
        "select_image_model": "🔄 <b>Выберите модель генерации изображений:</b>",
        "not_subscribed": (
            "🔒 <b>Для использования модуля необходимо подписаться на канал:</b>\n"
            "@mwapi_dev"
        ),
        "rate_limit": "⏱ <b>Подождите {} секунд между запросами</b>"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "API_URL",
            "http://146.19.48.160:25974/generate",
            "URL API для текста",

            "IMAGE_API_URL",
            "http://146.19.48.160:25701/generate_image",
            "URL API для изображений",

            "MODEL",
            "gemini-pro",
            "Модель по умолчанию для текста",

            "IMAGE_MODEL",
            "anything-v5",
            "Модель по умолчанию для изображений",

            "RATE_LIMIT",
            2,
            "Задержка между запросами (в секундах)"
        )
        self.last_request = 0
        self.models = {
            "antigpt": "Anti-GPT",
            "gemini-pro": "Gemini 1.5 Pro",
            "gpt4": "GPT-4",
            "gemini": "Gemini 1.5 Flash",
            "gemma-7b-it": "Gemma-7b-it",
            "llama-3-1": "llama-3.1-70b-versatile",
            "gpt3": "GPT-3",
            "gpt4-turbo": "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "pixtral-12b-2409": "Pixtral 12B",
            "open-codestral-mamba": "Open Codestral Mamba",
            "gemma2-9b": "Gemma2-9B",
            "Ilama-3-1": "Ilama 3.1",
            "llama-3-1-70b-specdec": "Llama 3.1-70B Specdec",
            "open-mistral-nemo": "Open Mistral Nemo",
            "claude-sonnet": "Claude Sonnet",
            "claude-3-haiku": "Claude 3 Haiku"
        }
        self.image_models = {
            "anything-v5": "Anything v5",
            "dreamshaper-v6": "DreamShaper v6",
            "dreamshaper-v5": "DreamShaper v5",
            "meina-v9": "Meina v9",
            "anything-v3": "Anything v3",
            "orangemix": "Orangemix"
        }

    async def _check_subscription(self, message: Message) -> bool:
        try:
            await self.client(GetParticipantRequest(
                channel="@mwapi_dev",
                participant=message.sender_id
            ))
            return True
        except UserNotParticipantError:
            await self.inline.form(
                message=message,
                text=self.strings["not_subscribed"],
                reply_markup=[
                    [
                        {"text": "📢 Подписаться", "url": "https://t.me/mwapi_dev"}
                    ],
                    [
                        {"text": "🔄 Проверить подписку", "callback": self._check_sub_callback}
                    ]
                ],
                silent=True
            )
            return False
        except Exception:
            return True

    async def _check_sub_callback(self, call: InlineCall):
        try:
            await self.client(GetParticipantRequest(
                channel="@mwapi_dev",
                participant=call.from_user.id
            ))
            await call.edit(
                "✅ <b>Спасибо за подписку!</b>\nТеперь вы можете использовать все функции модуля.",
                reply_markup=[[{"text": "🔥 Начать", "action": "close"}]]
            )
        except UserNotParticipantError:
            await call.answer("❌ Вы все ещё не подписаны на канал!", show_alert=True)
        except Exception:
            await call.answer("🤔 Не удалось проверить подписку", show_alert=True)

    def get_model_buttons(self, model_type="text"):
        models = self.models if model_type == "text" else self.image_models
        buttons = []
        row = []
        for model_key, model_name in models.items():
            if len(row) == 2:
                buttons.append(row)
                row = []
            row.append({
                "text": model_name,
                "callback": self.model_callback,
                "args": (model_key, model_type)
            })
        if row:
            buttons.append(row)
        buttons.append([{"text": "🔙 Закрыть", "action": "close"}])
        return buttons

    async def model_callback(self, call: InlineCall, model: str, model_type: str):
        if model_type == "text":
            self.config["MODEL"] = model
        else:
            self.config["IMAGE_MODEL"] = model
        await call.edit(
            self.strings["settings_header"].format(
                self.models[model] if model_type == "text" else self.image_models[model]
            ),
            reply_markup=self.get_model_buttons(model_type)
        )

    @loader.command()
    async def ai(self, message: Message):
        """🤖 Запрос к AI. Использование: .ai <запрос>"""
        if not await self._check_subscription(message):
            return

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_args"])
            return

        if time.time() - self.last_request < self.config["RATE_LIMIT"]:
            await utils.answer(
                message,
                self.strings["rate_limit"].format(self.config["RATE_LIMIT"])
            )
            return

        self.last_request = time.time()
        status = await utils.answer(message, self.strings["processing"])
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config["API_URL"],
                    json={
                        "prompt": args,
                        "model_name": self.config["MODEL"]
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=30
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    response_time = time.time() - start_time

                    await utils.answer(
                        status,
                        self.strings["response"].format(
                            self.models[self.config["MODEL"]],
                            result.get("response", "Нет ответа"),
                            response_time,
                            self.config["MODEL"]
                        )
                    )
        except Exception as e:
            await utils.answer(status, f"{self.strings['error']}\n\n<code>{str(e)}</code>")

    @loader.command()
    async def aiimage(self, message: Message):
        """🎨 Запрос на генерацию изображения. Использование: .aiimage <описание>"""
        if not await self._check_subscription(message):
            return

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_args"])
            return

        if time.time() - self.last_request < self.config["RATE_LIMIT"]:
            await utils.answer(
                message,
                self.strings["rate_limit"].format(self.config["RATE_LIMIT"])
            )
            return

        self.last_request = time.time()
        status = await utils.answer(message, self.strings["processing"])
        start_time = time.time()

        try:
            data = {
                "prompt": args,
                "model": self.config["IMAGE_MODEL"]
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(self.config["IMAGE_API_URL"], json=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            image_url = result.get("image_url", "")
            image_response = requests.get(image_url)
            response_time = time.time() - start_time

            image = BytesIO(image_response.content)
            image.name = "generated_image.png"

            await self.client.send_file(
                message.chat_id,
                image,
                caption=self.strings["image_response"].format(
                    response_time,
                    self.image_models[self.config["IMAGE_MODEL"]],
                    image_url
                ),
                reply_to=message.id
            )
            await status.delete()
        except requests.exceptions.RequestException as e:
            await utils.answer(status, f"{self.strings['error']}\n\n<code>{str(e)}</code>")
        except Exception as e:
            await utils.answer(status, f"{self.strings['error']}\n\n<code>{str(e)}</code>")

    @loader.command()
    async def aimodels(self, message: Message):
        """⚙️ Настройки и выбор модели для текста"""
        if not await self._check_subscription(message):
            return

        await self.inline.form(
            message=message,
            text=self.strings["settings_header"].format(
                self.models[self.config["MODEL"]]
            ),
            reply_markup=self.get_model_buttons("text")
        )

    @loader.command()
    async def aiimagemodels(self, message: Message):
        """⚙️ Настройки и выбор модели для генерации изображений"""
        if not await self._check_subscription(message):
            return

        await self.inline.form(
            message=message,
            text=self.strings["settings_header"].format(
                self.image_models[self.config["IMAGE_MODEL"]]
            ),
            reply_markup=self.get_model_buttons("image")
        )