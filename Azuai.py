# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import aiohttp
from .. import loader, utils
from telethon import events
import os
import tempfile
import asyncio # New import for sleep
from openai import AsyncOpenAI # Changed import for OnlySq provider
import base64 # Existing, ensure it's here for media handling
import mimetypes # Existing, ensure it's here for media handling

ONLYSQ_TEXT_MODELS = [
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "command-a-03-2025",
    "command-r7b-12-2024",
    "command-r-plus-04-2024",
    "command-r-plus",
    "command-r-08-2024",
    "command-r-03-2024",
    "command-r",
    "command",
    "command-nightly",
    "command-light",
    "command-light-nightly",
    "c4ai-aya-expanse-32b",
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4",
    "gpt-3.5-turbo",
    "o3-mini",
    "evil",
    "mistral-small-3.1"
]

@loader.tds
class AzuAI(loader.Module):
    """Модуль для взаимодействия с нейросетями Gemini, OpenRouter и OnlySq с выбором модели через кнопки"""
    strings = {
        "name": "AzuAI"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "GEMINI_API_KEY", "", "API-ключ для Gemini AI",
            "OPENROUTER_API_KEY", "", "API-ключ для OpenRouter",
            "ONLYSQ_API_KEY", "openai", "API-ключ для OnlySq (по умолчанию 'openai')", # Updated default value
            "DEFAULT_PROVIDER", 1, "Провайдер по умолчанию: 1 - Gemini, 2 - OpenRouter, 3 - OnlySq",
            "ONLYSQ_IMAGE_MODEL", "kandinsky", "Модель OnlySq для генерации изображений" # New config
        )
        self.selected_models = {"gemini": "gemini-2.5-flash-preview-05-20", "openrouter": "meta-llama/llama-3.1-8b-instruct:free", "onlysq": "o3-mini"} # Updated default model for OnlySq
        self.model_lists = {"gemini": [], "openrouter": [], "onlysq": []} # Add OnlySq to model lists
        self.chat_contexts = {} # Словарь для хранения состояния контекста по чатам
        self.chat_histories = {} # Словарь для хранения истории диалогов по чатам

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        # Загружаем сохраненные состояния из базы данных
        self.chat_contexts = self.db.get(self.strings["name"], "chat_contexts", {})
        self.chat_histories = self.db.get(self.strings["name"], "chat_histories", {})
        await self._fetch_models()

    async def _fetch_models(self):
        """Получить доступные модели Gemini, OpenRouter и OnlySq"""
        # Gemini
        if self.config["GEMINI_API_KEY"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.config['GEMINI_API_KEY']}"
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.model_lists["gemini"] = [model["name"] for model in data.get("models", []) if "generateContent" in model["supportedGenerationMethods"]] # Filter for models that support generateContent
                            print("Успешно получены модели Gemini")
                            print(f"Тело ответа Gemini Models (status 200): {data}")
                        else:
                            error_text = await response.text()
                            print(f"Ошибка получения моделей Gemini. Статус: {response.status}, Ответ: {error_text[:200]}...")
                            self.model_lists["gemini"] = []
                except Exception as e:
                    print(f"Исключение при получении моделей Gemini: {str(e)}")
                    self.model_lists["gemini"] = []
        else:
             print("API-ключ Gemini не установлен, пропуск получения моделей.")
             self.model_lists["gemini"] = []

        # OpenRouter (только бесплатные)
        if self.config["OPENROUTER_API_KEY"]:
            url = "https://openrouter.ai/api/v1/models"
            headers = {"Authorization": f"Bearer {self.config['OPENROUTER_API_KEY']}"}
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            all_openrouter_models = [model["id"] for model in data.get("data", [])]
                            self.model_lists["openrouter"] = [
                                model_id for model_id in all_openrouter_models
                                if model_id.startswith('google/') or model_id.startswith('deepseek/') or model_id.startswith('meta-llama/')
                            ]
                            print("Успешно получены все модели OpenRouter.")
                            print(f"Общее количество моделей до фильтрации: {len(all_openrouter_models)}")
                            print(f"Количество моделей OpenRouter после фильтрации: {len(self.model_lists['openrouter'])}")
                            print("Список отфильтрованных моделей OpenRouter:")
                            for model_id in self.model_lists["openrouter"]:
                                print(f"- {model_id}")
                            print(f"Тело ответа OpenRouter Models (status 200): {data}")
                        else:
                            error_text = await response.text()
                            print(f"Ошибка получения моделей OpenRouter. Статус: {response.status}, Ответ: {error_text}")
                            self.model_lists["openrouter"] = []
                except Exception as e:
                    print(f"Исключение при получении моделей OpenRouter: {str(e)}")
                    self.model_lists["openrouter"] = []
        else:
            print("API-ключ OpenRouter не установлен, пропуск получения моделей.")
            self.model_lists["openrouter"] = []

        # OnlySq (используем предоставленный список моделей)
        if self.config["ONLYSQ_API_KEY"]:
            self.model_lists["onlysq"] = ONLYSQ_TEXT_MODELS # Directly assign the predefined list
            print("Модели OnlySq загружены из предопределенного списка.")
            print(f"Количество моделей OnlySq: {len(self.model_lists['onlysq'])}")
            print("Список моделей OnlySq:")
            for model_id in self.model_lists["onlysq"]:
                print(f"- {model_id}")
        else:
            print("API-ключ OnlySq не установлен, пропуск загрузки моделей.")
            self.model_lists["onlysq"] = []

    def _create_model_buttons(self, service):
        """Создать инлайн-кнопки для выбора модели"""
        buttons = []
        models = self.model_lists.get(service, [])
        if not models:
            return []
        for model in models:
            buttons.append([{"text": model, "callback": self._set_model, "args": (service, model)}])
        buttons.append([{"text": "⬅️ Назад", "callback": self._back_to_services}])
        return buttons

    async def aicfgcmd(self, message):
        """⚙️ Настроить провайдера и модель, установить API-ключи через конфигурацию модуля"""
        await self.inline.form(
            text="⚙️ <b>Настройки AIModule:</b>\n\nAPI-ключи устанавливаются в конфигурации модуля (через файл или команды setkey, если доступны).",
            message=message,
            reply_markup=[
                [{"text": "Выбор провайдера", "callback": self._show_settings_menu, "args": ("providers",)}],
                [{"text": "Выбор модели", "callback": self._show_settings_menu, "args": ("models_service",)}]
            ]
        )

    async def _show_settings_menu(self, call, menu_type):
        text = ""
        reply_markup = []

        if menu_type == "main":
            text = "⚙️ <b>Настройки AIModule:</b>\n\nAPI-ключи устанавливаются в конфигурации модуля (через файл или команды setkey, если доступны)."
            reply_markup = [
                [{"text": "Выбор провайдера", "callback": self._show_settings_menu, "args": ("providers",)}],
                [{"text": "Выбор модели", "callback": self._show_settings_menu, "args": ("models_service",)}]
            ]
        elif menu_type == "providers":
            current_provider = self.config["DEFAULT_PROVIDER"]
            def get_provider_button(provider_id, provider_name):
                text = provider_name
                if current_provider == provider_id:
                    text += "🟣"
                return {"text": text, "callback": self._set_provider, "args": (provider_id,)}

            text = "🔧 <b>Выберите провайдера по умолчанию:</b>"
            reply_markup = [
                [get_provider_button(1, "Gemini")],
                [get_provider_button(2, "OpenRouter")],
                [get_provider_button(3, "OnlySq")], # New OnlySq button
                [{"text": "⬅️ Назад", "callback": self._show_settings_menu, "args": ("main",)}]
            ]
        elif menu_type == "models_service":
            text = "🔧 <b>Выберите сервис для выбора модели:</b>"
            reply_markup = [
                [{"text": "Gemini", "callback": self._show_models, "args": ("gemini",)}],
                [{"text": "OpenRouter", "callback": self._show_models, "args": ("openrouter",)}],
                [{"text": "OnlySq", "callback": self._show_models, "args": ("onlysq",)}], # New OnlySq button
                [{"text": "⬅️ Назад", "callback": self._show_settings_menu, "args": ("main",)}]
            ]

        await call.edit(text=text, reply_markup=reply_markup)

    async def _set_provider(self, call, provider_id):
        """Установить провайдера по умолчанию из инлайн-кнопки"""
        self.config["DEFAULT_PROVIDER"] = provider_id
        provider_name = ""
        if provider_id == 1: provider_name = "Gemini"
        elif provider_id == 2: provider_name = "OpenRouter"
        elif provider_id == 3: provider_name = "OnlySq"
        await call.edit(f"Провайдер по умолчанию установлен: {provider_name}")
        await asyncio.sleep(1) # Добавляем небольшую задержку
        await self._show_settings_menu(call, "providers") # Обновляем меню с индикатором

    async def _show_models(self, call, service):
        """Показать инлайн-кнопки для выбора модели"""
        models = self.model_lists.get(service, [])
        if not models:
            await call.edit(f"⚠️ <b>Нет доступных моделей для {service}.</b> Проверьте API-ключ и попробуйте снова.")
            await self._show_settings_menu(call, "models_service") # Возвращаем пользователя в меню выбора сервиса
            return
        buttons = []
        selected_model = self.selected_models.get(service)
        for model in models:
            button_text = model
            if model == selected_model:
                button_text += "🟣"
            buttons.append([{"text": button_text, "callback": self._set_model, "args": (service, model)}])
        buttons.append([
            {"text": "⬅️ Назад", "callback": self._show_settings_menu, "args": ("models_service",)}
        ])
        await call.edit(
            f"🔧 <b>Выберите модель для {service}:</b>",
            reply_markup=buttons
        )

    async def _set_model(self, call, service, model):
        """Установить выбранную модель из инлайн-кнопки"""
        self.selected_models[service] = model
        await call.edit(f"✅ <b>Модель выбрана:</b> {model}")
        await asyncio.sleep(1) # Добавляем небольшую задержку
        await self._show_models(call, service) # Обновляем меню с индикатором

    async def _back_to_aicfg(self, call):
        # Эта функция больше не нужна, так как _show_settings_menu теперь обрабатывает навигацию назад
        pass

    async def askcmd(self, message):
        """Задать вопрос ИИ. Пример: .ask ваш вопрос или ответить на сообщение с .ask"""
        query = utils.get_args_raw(message).strip()
        media_path = None # Инициализируем media_path здесь, чтобы она всегда была определена

        # Проверяем, является ли сообщение ответом и загружаем медиа/текст из него, если есть
        if message.is_reply:
            try:
                reply_message = await message.get_reply_message()
                if reply_message:
                    # Если есть текст в ответном сообщении, добавляем его к запросу, если запрос не пуст
                    # или используем как основной запрос, если аргументы пустые
                    if reply_message.text:
                        if not query:
                            query = reply_message.text.strip()
                        else:
                            query += "\n" + reply_message.text.strip()

                    if reply_message.photo or (reply_message.document and reply_message.document.mime_type and reply_message.document.mime_type.startswith('image/')):
                        # Обрабатываем фото и документы, которые являются изображениями
                        processing_message = await utils.answer(message, "🧠 Обнаружено фото/изображение. Загрузка...")
                        try:
                            media_path = await reply_message.download_media(file=tempfile.gettempdir())
                            await processing_message.edit("🧠 Изображение загружено. Обработка запроса...")
                        except Exception as e:
                            await utils.answer(message, f"Ошибка при загрузке изображения: {str(e)}")
                            return
                    elif reply_message.document:
                        # Обрабатываем общие документы
                        mime_type = reply_message.document.mime_type
                        if mime_type and (mime_type.startswith('text/') or mime_type in ['application/json', 'application/xml', 'text/html', 'text/csv', 'application/javascript', 'application/x-sh', 'application/x-python']):
                            processing_message = await utils.answer(message, f"🧠 Обнаружен текстовый файл ({mime_type}). Загрузка и чтение...")
                            try:
                                temp_file_path = await reply_message.download_media(file=tempfile.gettempdir())
                                with open(temp_file_path, 'r', encoding='utf-8') as f:
                                    file_content = f.read()
                                os.remove(temp_file_path) # Удаляем временный файл
                                if not query:
                                    query = file_content
                                else:
                                    query += "\n\n--- Содержимое файла ---\n" + file_content
                                await processing_message.edit("🧠 Файл прочитан. Обработка запроса...")
                            except Exception as e:
                                await utils.answer(message, f"Ошибка при загрузке или чтении файла: {str(e)}")
                                return
                        else:
                            # Для любых других типов документов (включая видео)
                            await utils.answer(message, f"Примечание: Прямая обработка файлов типа '{mime_type}' не поддерживается в текущей конфигурации. Будет обработан только текстовый запрос.")
                            try:
                                # Попытка загрузить для очистки, но не использовать media_path для ИИ
                                temp_file_to_cleanup = await reply_message.download_media(file=tempfile.gettempdir())
                                os.remove(temp_file_to_cleanup)
                            except Exception: # Игнорируем ошибки, если загрузка не удалась только для очистки
                                pass
            except Exception as e:
                await utils.answer(message, f"Ошибка при получении текста из ответа или загрузке медиа: {str(e)}")
                return

        if not query and not media_path:
            await utils.answer(message, "Пожалуйста, введите запрос или ответьте на сообщение с текстом, фото или видео. Пример: <code>.ask ваш вопрос</code>")
            return
        
        service = ""
        if self.config["DEFAULT_PROVIDER"] == 1: service = "gemini"
        elif self.config["DEFAULT_PROVIDER"] == 2: service = "openrouter"
        elif self.config["DEFAULT_PROVIDER"] == 3: service = "onlysq"

        # Отправляем сообщение о начале обработки запроса
        # processing_message = await utils.answer(message, "🧠 Обработка запроса...") # Закомментирована для предотвращения удаления сообщения

        chat_id = str(message.chat_id)
        is_context_enabled = self.chat_contexts.get(chat_id, False)
        history = self.chat_histories.get(chat_id, [])

        if is_context_enabled:
            # Добавляем текущий запрос пользователя в историю для контекста
            # Если есть и текст и медиа, добавляем только текст для истории, т.к. история чата текстовая
            if query:
                history.append({"role": "user", "content": query})
                self.chat_histories[chat_id] = history

        # Логика поиска удалена, т.к. Gemini сам решает использовать ли Grounding (поиск)

        ai_response_message = None
        if service == "gemini":
            ai_response_message = await self._ask_gemini(message, query, history if is_context_enabled else [], media_path) # Передаем историю и медиафайл
        elif service == "openrouter":
            ai_response_message = await self._ask_openrouter(message, query, history if is_context_enabled else [], media_path) # Передаем историю и медиафайл
        elif service == "onlysq":
            ai_response_message = await self._ask_onlysq(message, query, history if is_context_enabled else [], media_path) # New call for OnlySq

        # Удаляем сообщение "Обработка запроса..."
        # if processing_message:
        #     await processing_message.delete() # Закомментирована для предотвращения удаления сообщения

        # Удаляем временный медиафайл, если он был загружен
        if media_path and os.path.exists(media_path):
            os.remove(media_path)

        # После ответа ИИ, если контекст включен, добавляем кнопку очистки диалога
        # if is_context_enabled and ai_response_message:
        #     await self.inline.form(
        #         text=ai_response_message.text, # Используем текст ответа ИИ
        #         message=ai_response_message, # Привязываем к сообщению с ответом ИИ
        #         reply_markup=[[{"text": "🗑️ Очистить диалог", "callback": self._clear_chat_history_callback}]],
        #         disable_security=True # Разрешаем без безопасности для работы с кнопками
        #     )

    async def _ask_gemini(self, message, query, history=[], media_path=None): # Добавляем history и media_path как аргументы
        api_key = self.config["GEMINI_API_KEY"]
        if not api_key:
            await utils.answer(message, "API-ключ для Gemini не установлен. Используйте <code>.setkey {{gemini,openrouter,onlysq}} &lt;ваш_ключ&gt;</code>.")
            return

        # Взаимодействие с Gemini API через HTTP с использованием Grounding
        model_id = self.selected_models['gemini'].replace('models/', '')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}

        # Формируем список сообщений для контекста
        contents = []
        for msg in history:
            contents.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})
        
        # Добавляем текущий запрос пользователя и медиафайл, если есть
        parts = []
        if query:
            parts.append({"text": query})
        if media_path: # media_path будет содержать только путь к изображению
            try:
                with open(media_path, "rb") as f:
                    encoded_media = base64.b64encode(f.read()).decode('utf-8')

                mime_type, _ = mimetypes.guess_type(media_path)
                if mime_type and mime_type.startswith('image/'):
                    parts.append({"inline_data": {"mime_type": mime_type, "data": encoded_media}})
                else:
                    # Этот случай не должен быть достигнут, если askcmd правильно фильтрует media_path
                    await utils.answer(message, "Неподдерживаемый тип медиафайла для Gemini (не изображение). Будет обработан только текст запроса.")

            except Exception as e:
                await utils.answer(message, f"Ошибка при кодировании медиафайла для Gemini: {str(e)}")
                return

        if not parts:
            await utils.answer(message, "Не удалось сформировать части запроса для Gemini (нет текста или медиа).")
            return

        contents.append({"role": "user", "parts": parts})

        payload = {
            "contents": contents,
            "tools": [
                {
                    "googleSearch": {} # Оставляем Grounding для автоматического поиска
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        # Отправляем ошибку новым сообщением
                        await utils.answer(message, f"Ошибка при получении ответа от Gemini (HTTP): Status {response.status}: {error_text[:200]}...")
                        return
                    data = await response.json()

                    # Обработка ответа
                    if data and "candidates" in data and data["candidates"]:
                         answer_parts = []
                         for part in data["candidates"][0]["content"]["parts"]:
                              if "text" in part:
                                   answer_parts.append(part["text"])
                              if "groundingAttributions" in part:
                                   for attribution in part["groundingAttributions"]:
                                        if "uri" in attribution:
                                             answer_parts.append(f" [[{attribution.get('title', 'ссылка')}]]({'uri'})")

                         answer = "".join(answer_parts)

                         if not answer:
                             if data["candidates"][0].get("finishReason") == "SAFETY" or data["candidates"][0].get("blockReason"):
                                  block_reason = data["candidates"][0].get("blockReason") or data["candidates"][0].get("finishReason")
                                  await utils.answer(message, f"⚠️ Запрос к Gemini заблокирован по причине безопасности: {block_reason}")
                             else:
                                  await utils.answer(message, "Ошибка при получении ответа от Gemini (HTTP): Получен пустой ответ от API")
                         else:
                             await utils.answer(message, f"<b>Gemini ({self.selected_models['gemini']}):</b>\n{answer}")
                             # Если контекст включен, добавляем ответ ИИ в историю
                             if str(message.chat_id) in self.chat_contexts and self.chat_contexts[str(message.chat_id)]:
                                self.chat_histories[str(message.chat_id)].append({"role": "model", "content": answer})
                                self.db.set(self.strings["name"], "chat_histories", self.chat_histories) # Сохраняем в БД

                    elif data and "promptFeedback" in data and data["promptFeedback"].get("blockReason"):
                         block_reason = data["promptFeedback"]["blockReason"]
                         await utils.answer(message, f"⚠️ Запрос к Gemini заблокирован: {block_reason}")
                    else:
                         await utils.answer(message, "Ошибка при получении ответа от Gemini (HTTP): Неожиданный формат ответа от API")

            except Exception as e:
                await utils.answer(message, f"Ошибка при получении ответа от Gemini (HTTP): {str(e)}")

    async def _ask_openrouter(self, message, query, history=[], media_path=None): # Добавляем history и media_path как аргументы
        api_key = self.config["OPENROUTER_API_KEY"]
        if not api_key:
            await utils.answer(message, "API-ключ для OpenRouter не установлен. Используйте <code>.setkey {{gemini,openrouter,onlysq}} &lt;ваш_ключ&gt;</code>.")
            return
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Формируем список сообщений для контекста
        messages = []
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # OpenRouter не поддерживает мультимодальный ввод из коробки через свой `/chat/completions` API для всех моделей.
        # Некоторые модели могут иметь специфическую поддержку или требовать другой эндпоинт.
        # Пока что, если есть медиа, мы просто сообщим, что его обработка для OpenRouter ограничена.
        if media_path:
            await utils.answer(message, "Примечание: OpenRouter в настоящее время не поддерживает прямую мультимодальную обработку изображений/видео через текущий API. Будет обработан только текст запроса.")

        messages.append({"role": "user", "content": query})

        payload = {
            "model": self.selected_models["openrouter"],
            "messages": messages
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        await utils.answer(message, f"Ошибка при получении ответа от OpenRouter: Status {response.status}: {error_text[:200]}...")
                        return
                    data = await response.json()
                    answer = data["choices"][0]["message"]["content"]
                    await utils.answer(message, f"<b>OpenRouter ({self.selected_models['openrouter']}):</b>\n{answer}")
                    # Если контекст включен, добавляем ответ ИИ в историю
                    if str(message.chat_id) in self.chat_contexts and self.chat_contexts[str(message.chat_id)]:
                        self.chat_histories[str(message.chat_id)].append({"role": "model", "content": answer})
                        self.db.set(self.strings["name"], "chat_histories", self.chat_histories) # Сохраняем в БД
            except Exception as e:
                await utils.answer(message, f"Ошибка при получении ответа от OpenRouter: {str(e)}")

    async def _ask_onlysq(self, message, query, history=[], media_path=None): # New function for OnlySq
        api_key = self.config["ONLYSQ_API_KEY"]
        if not api_key:
            await utils.answer(message, "API-ключ для OnlySq не установлен. Используйте <code>.setkey {{gemini,openrouter,onlysq}} &lt;ваш_ключ&gt;</code>.")
            return
        
        client = AsyncOpenAI(
            base_url="https://api.onlysq.ru/ai/openai",
            api_key=api_key,
        )

        messages = []
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        content_parts = []
        if query:
            content_parts.append({"type": "text", "text": query})
        
        if media_path: # Check for image media
            try:
                with open(media_path, "rb") as f:
                    encoded_media = base64.b64encode(f.read()).decode('utf-8')
                mime_type, _ = mimetypes.guess_type(media_path)
                if mime_type and mime_type.startswith('image/'):
                    content_parts.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded_media}"}})
                else:
                    await utils.answer(message, "OnlySq: Неподдерживаемый тип медиафайла (не изображение). Будет обработан только текст запроса.")
            except Exception as e:
                await utils.answer(message, f"Ошибка при кодировании медиафайла для OnlySq: {str(e)}")
                return

        if not content_parts:
            await utils.answer(message, "OnlySq: Не удалось сформировать части запроса (нет текста или медиа).")
            return

        messages.append({"role": "user", "content": content_parts})

        try:
            completion = await client.chat.completions.create(
                model=self.selected_models["onlysq"],
                messages=messages,
            )
            answer = completion.choices[0].message.content
            await utils.answer(message, f"<b>OnlySq ({self.selected_models['onlysq']}):</b>\n{answer}")
            if str(message.chat_id) in self.chat_contexts and self.chat_contexts[str(message.chat_id)]:
                self.chat_histories[str(message.chat_id)].append({"role": "model", "content": answer})
                self.db.set(self.strings["name"], "chat_histories", self.chat_histories) # Save to DB
        except Exception as e:
            await utils.answer(message, f"Ошибка при получении ответа от OnlySq: {str(e)}")

    async def chatcmd(self, message):
        """Включает/выключает режим контекстного диалога."""
        chat_id = str(message.chat_id)
        if chat_id not in self.chat_contexts:
            self.chat_contexts[chat_id] = False # По умолчанию выключен

        self.chat_contexts[chat_id] = not self.chat_contexts[chat_id] # Переключаем состояние
        self.db.set(self.strings["name"], "chat_contexts", self.chat_contexts) # Сохраняем в БД

        status = "включен" if self.chat_contexts[chat_id] else "выключен"
        await utils.answer(message, f"Режим контекстного диалога для этого чата {status}.")

    async def clearchatcmd(self, message):
        """Очищает историю контекстного диалога для текущего чата."""
        chat_id = str(message.chat_id)
        if chat_id in self.chat_histories:
            del self.chat_histories[chat_id]
            self.db.set(self.strings["name"], "chat_histories", self.chat_histories)
            await utils.answer(message, "История диалога очищена.")
        else:
            await utils.answer(message, "История диалога уже пуста.")

    # async def _clear_chat_history_callback(self, call):
    #     """Callback для очистки истории диалога."""
    #     chat_id = str(call.chat_id)
    #     if chat_id in self.chat_histories:
    #         del self.chat_histories[chat_id]
    #         self.db.set(self.strings["name"], "chat_histories", self.chat_histories)
    #         await call.edit("История диалога очищена.", reply_markup=None)
    #     else:
    #         await call.edit("История диалога уже пуста.", reply_markup=None)

    async def imgcmd(self, message):
        """Генерирует изображение с помощью OnlySq. Пример: .img ваш запрос"""
        query = utils.get_args_raw(message).strip()
        if not query:
            await utils.answer(message, "Пожалуйста, введите запрос для генерации изображения. Пример: <code>.img красивый закат на пляже</code>")
            return

        # Отправляем сообщение о начале обработки запроса
        processing_message = await utils.answer(message, "🧠 Запрос на генерацию изображения отправлен...")

        image_path = await self._generate_image_onlysq(message, query)

        if processing_message:
            await processing_message.delete()

        if image_path:
            try:
                await self.client.send_file(
                    message.chat_id,
                    image_path,
                    caption=f"🖼️ Изображение сгенерировано по запросу: <i>{query}</i>",
                    reply_to=message.id
                )
            except Exception as e:
                await utils.answer(message, f"Ошибка при отправке изображения: {str(e)}")
            finally:
                if os.path.exists(image_path):
                    os.remove(image_path)
        else:
            await utils.answer(message, "Не удалось сгенерировать изображение.")

    async def _generate_image_onlysq(self, message, prompt):
        """Генерирует изображение с помощью OnlySq API."""
        api_key = self.config["ONLYSQ_API_KEY"]
        if not api_key:
            api_key = "openai" # Use "openai" as default if key is empty

        image_model = self.config["ONLYSQ_IMAGE_MODEL"]
        url = "https://api.onlysq.ru/ai/imagen"
        headers = {"Content-Type": "application/json"}

        payload = {
            "model": image_model,
            "prompt": prompt,
            "width": 1024, # Default width
            "height": 1024, # Default height
            "count": 1 # Number of images to generate
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        await utils.answer(message, f"Ошибка при генерации изображения от OnlySq (HTTP): Status {response.status}: {error_text[:200]}...")
                        return None
                    
                    data = await response.json()
                    if data and "files" in data and data["files"]:
                        # Get the first image from the list of files (base64 encoded)
                        encoded_image = data["files"][0]
                        decoded_image = base64.b64decode(encoded_image)

                        # Save to a temporary file
                        temp_image_path = os.path.join(tempfile.gettempdir(), "generated_image.png")
                        with open(temp_image_path, "wb") as f:
                            f.write(decoded_image)
                        
                        return temp_image_path
                    else:
                        await utils.answer(message, "Не удалось получить данные изображения от OnlySq.")
                        return None
        except Exception as e:
            await utils.answer(message, f"Ошибка при запросе к OnlySq Imagen API: {str(e)}")
            return None
