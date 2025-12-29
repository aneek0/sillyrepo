# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import aiohttp
from .. import loader, utils
from telethon import events
import os
import tempfile
import asyncio
from openai import AsyncOpenAI
import base64
import mimetypes
import json

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
            "ONLYSQ_API_KEY", "openai", "API-ключ для OnlySq (по умолчанию 'openai')",
            "TAVILY_API_KEY", "", "API-ключ для Tavily (поиск в интернете)",
            "DEFAULT_PROVIDER", 1, "Провайдер по умолчанию: 1 - Gemini, 2 - OpenRouter, 3 - OnlySq",
            "ONLYSQ_IMAGE_MODEL", "kandinsky", "Модель OnlySq для генерации изображений"
        )
        self.selected_models = {"gemini": "gemini-2.5-flash-preview-09-2025", "openrouter": "meta-llama/llama-3.1-8b-instruct:free", "onlysq": "gemini-3-flash"}
        self.model_lists = {"gemini": [], "openrouter": [], "onlysq": []}
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
                            self.model_lists["gemini"] = [model["name"] for model in data.get("models", []) if "generateContent" in model["supportedGenerationMethods"]]
                            print("Успешно получены модели Gemini")
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

        # OnlySq
        if self.config["ONLYSQ_API_KEY"]:
            url = "https://api.onlysq.ru/ai/models"
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Extract keys from the "models" dictionary
                            self.model_lists["onlysq"] = list(data.get("models", {}).keys())
                            print("Успешно получены модели OnlySq.")
                            print(f"Количество моделей OnlySq: {len(self.model_lists['onlysq'])}")
                        else:
                            error_text = await response.text()
                            print(f"Ошибка получения моделей OnlySq. Статус: {response.status}, Ответ: {error_text}")
                            self.model_lists["onlysq"] = []
                except Exception as e:
                    print(f"Исключение при получении моделей OnlySq: {str(e)}")
                    self.model_lists["onlysq"] = []
        else:
            print("API-ключ OnlySq не установлен, пропуск загрузки моделей.")
            self.model_lists["onlysq"] = []

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
                [get_provider_button(3, "OnlySq")],
                [{"text": "⬅️ Назад", "callback": self._show_settings_menu, "args": ("main",)}]
            ]
        elif menu_type == "models_service":
            text = "🔧 <b>Выберите сервис для выбора модели:</b>"
            reply_markup = [
                [{"text": "Gemini", "callback": self._show_models, "args": ("gemini",)}],
                [{"text": "OpenRouter", "callback": self._show_models, "args": ("openrouter",)}],
                [{"text": "OnlySq", "callback": self._show_models, "args": ("onlysq",)}],
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
        await asyncio.sleep(1)
        await self._show_settings_menu(call, "providers")

    async def _show_models(self, call, service, page=0):
        """Показать инлайн-кнопки для выбора модели"""
        models = self.model_lists.get(service, [])
        if not models:
            await call.edit(f"⚠️ <b>Нет доступных моделей для {service}.</b> Проверьте API-ключ и попробуйте снова.")
            await self._show_settings_menu(call, "models_service")
            return

        # Динамический расчет лимита для равномерного распределения по страницам
        # Telegram лимит кнопок ~100. Берем 80 для безопасности.
        MAX_BUTTONS = 80
        total_models = len(models)
        
        if total_models <= MAX_BUTTONS:
            limit = total_models
        else:
            # Если моделей больше лимита, делим на минимально возможное количество страниц
            num_pages = (total_models + MAX_BUTTONS - 1) // MAX_BUTTONS
            limit = (total_models + num_pages - 1) // num_pages
            
        if limit == 0: limit = 1

        total_pages = (total_models + limit - 1) // limit
        
        if page < 0: page = 0
        if page >= total_pages: page = total_pages - 1
        
        offset = page * limit
        current_models = models[offset:offset + limit]

        buttons = []
        selected_model = self.selected_models.get(service)
        for model in current_models:
            button_text = model
            if model == selected_model:
                button_text += "🟣"
            buttons.append([{"text": button_text, "callback": self._set_model, "args": (service, model, page)}])
        
        nav = []
        if total_pages > 1:
            if page > 0:
                nav.append({"text": "⬅️", "callback": self._show_models, "args": (service, page - 1)})
            
            nav.append({"text": f"{page + 1}/{total_pages}", "callback": self._show_models, "args": (service, page)})

            if page < total_pages - 1:
                nav.append({"text": "➡️", "callback": self._show_models, "args": (service, page + 1)})
            
            buttons.append(nav)

        buttons.append([
            {"text": "⬅️ Назад", "callback": self._show_settings_menu, "args": ("models_service",)}
        ])
        await call.edit(
            f"🔧 <b>Выберите модель для {service}:</b>",
            reply_markup=buttons
        )

    async def _set_model(self, call, service, model, page=0):
        """Установить выбранную модель из инлайн-кнопки"""
        self.selected_models[service] = model
        await call.edit(f"✅ <b>Модель выбрана:</b> {model}")
        await asyncio.sleep(1)
        await self._show_models(call, service, page)

    async def askcmd(self, message):
        """Задать вопрос ИИ. Пример: .ask ваш вопрос или ответить на сообщение с .ask"""
        query = utils.get_args_raw(message).strip()
        media_path = None

        if message.is_reply:
            try:
                reply_message = await message.get_reply_message()
                if reply_message:
                    if reply_message.text:
                        if not query:
                            query = reply_message.text.strip()
                        else:
                            query += "\n" + reply_message.text.strip()

                    if reply_message.photo or (reply_message.document and reply_message.document.mime_type and reply_message.document.mime_type.startswith('image/')):
                        processing_message = await utils.answer(message, "🧠 Обнаружено фото/изображение. Загрузка...")
                        try:
                            media_path = await reply_message.download_media(file=tempfile.gettempdir())
                            await processing_message.edit("🧠 Изображение загружено. Обработка запроса...")
                        except Exception as e:
                            await utils.answer(message, f"Ошибка при загрузке изображения: {str(e)}")
                            return
                    elif reply_message.document:
                        mime_type = reply_message.document.mime_type
                        if mime_type and (mime_type.startswith('text/') or mime_type in ['application/json', 'application/xml', 'text/html', 'text/csv', 'application/javascript', 'application/x-sh', 'application/x-python']):
                            processing_message = await utils.answer(message, f"🧠 Обнаружен текстовый файл ({mime_type}). Загрузка и чтение...")
                            try:
                                temp_file_path = await reply_message.download_media(file=tempfile.gettempdir())
                                with open(temp_file_path, 'r', encoding='utf-8') as f:
                                    file_content = f.read()
                                os.remove(temp_file_path)
                                if not query:
                                    query = file_content
                                else:
                                    query += "\n\n--- Содержимое файла ---\n" + file_content
                                await processing_message.edit("🧠 Файл прочитан. Обработка запроса...")
                            except Exception as e:
                                await utils.answer(message, f"Ошибка при загрузке или чтении файла: {str(e)}")
                                return
                        else:
                            await utils.answer(message, f"Примечание: Прямая обработка файлов типа '{mime_type}' не поддерживается в текущей конфигурации. Будет обработан только текстовый запрос.")
                            try:
                                temp_file_to_cleanup = await reply_message.download_media(file=tempfile.gettempdir())
                                os.remove(temp_file_to_cleanup)
                            except Exception:
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

        chat_id = str(message.chat_id)
        is_context_enabled = self.chat_contexts.get(chat_id, False)
        history = self.chat_histories.get(chat_id, [])

        if is_context_enabled:
            if query:
                history.append({"role": "user", "content": query})
                self.chat_histories[chat_id] = history

        if service == "gemini":
            await self._ask_gemini(message, query, history if is_context_enabled else [], media_path)
        elif service == "openrouter":
            await self._ask_openrouter(message, query, history if is_context_enabled else [], media_path)
        elif service == "onlysq":
            await self._ask_onlysq(message, query, history if is_context_enabled else [], media_path)

        if media_path and os.path.exists(media_path):
            os.remove(media_path)

    async def _ask_gemini(self, message, query, history=[], media_path=None):
        api_key = self.config["GEMINI_API_KEY"]
        if not api_key:
            await utils.answer(message, "API-ключ для Gemini не установлен. Используйте <code>.setkey {{gemini,openrouter,onlysq}} &lt;ваш_ключ&gt;</code>.")
            return

        model_id = self.selected_models['gemini'].replace('models/', '')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}

        contents = []
        for msg in history:
            contents.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})
        
        parts = []
        if query:
            parts.append({"text": query})
        if media_path:
            try:
                with open(media_path, "rb") as f:
                    encoded_media = base64.b64encode(f.read()).decode('utf-8')

                mime_type, _ = mimetypes.guess_type(media_path)
                if mime_type and mime_type.startswith('image/'):
                    parts.append({"inline_data": {"mime_type": mime_type, "data": encoded_media}})
                else:
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
            "tools": [{"googleSearch": {}}]
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        await utils.answer(message, f"Ошибка при получении ответа от Gemini (HTTP): Status {response.status}: {error_text[:200]}...")
                        return
                    data = await response.json()

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
                             if str(message.chat_id) in self.chat_contexts and self.chat_contexts[str(message.chat_id)]:
                                self.chat_histories[str(message.chat_id)].append({"role": "model", "content": answer})
                                self.db.set(self.strings["name"], "chat_histories", self.chat_histories)

                    elif data and "promptFeedback" in data and data["promptFeedback"].get("blockReason"):
                         block_reason = data["promptFeedback"]["blockReason"]
                         await utils.answer(message, f"⚠️ Запрос к Gemini заблокирован: {block_reason}")
                    else:
                         await utils.answer(message, "Ошибка при получении ответа от Gemini (HTTP): Неожиданный формат ответа от API")

            except Exception as e:
                await utils.answer(message, f"Ошибка при получении ответа от Gemini (HTTP): {str(e)}")

    async def _ask_openrouter(self, message, query, history=[], media_path=None):
        api_key = self.config["OPENROUTER_API_KEY"]
        if not api_key:
            await utils.answer(message, "API-ключ для OpenRouter не установлен. Используйте <code>.setkey {{gemini,openrouter,onlysq}} &lt;ваш_ключ&gt;</code>.")
            return
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        for msg in history:
            role = "assistant" if msg["role"] == "model" else msg["role"]
            messages.append({"role": role, "content": msg["content"]})
        
        if media_path:
            await utils.answer(message, "Примечание: OpenRouter в настоящее время не поддерживает прямую мультимодальную обработку изображений/видео через текущий API. Будет обработан только текст запроса.")

        messages.append({"role": "user", "content": query})

        # Определение tool для поиска через Tavily
        tools = []
        if self.config["TAVILY_API_KEY"]:
            tools = [{
                "type": "function",
                "function": {
                    "name": "search_internet",
                    "description": "Поиск актуальной информации в интернете. Используй эту функцию, когда нужно найти свежую информацию, новости, факты или данные, которые могут измениться со временем.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Поисковый запрос для поиска в интернете"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }]

        payload = {
            "model": self.selected_models["openrouter"],
            "messages": messages
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with aiohttp.ClientSession() as session:
            try:
                max_iterations = 3
                iteration = 0
                
                while iteration < max_iterations:
                    async with session.post(url, json=payload, headers=headers) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            await utils.answer(message, f"Ошибка при получении ответа от OpenRouter: Status {response.status}: {error_text[:200]}...")
                            return
                        data = await response.json()
                        
                        message_data = data["choices"][0]["message"]
                        
                        # Проверяем, есть ли tool calls
                        if "tool_calls" in message_data and message_data["tool_calls"]:
                            # Добавляем ответ модели в историю
                            messages.append(message_data)
                            
                            # Выполняем tool calls
                            for tool_call in message_data["tool_calls"]:
                                if tool_call["function"]["name"] == "search_internet":
                                    args = json.loads(tool_call["function"]["arguments"])
                                    search_query = args.get("query", query)
                                    
                                    search_results = await self._search_tavily(search_query)
                                    if search_results:
                                        messages.append({
                                            "role": "tool",
                                            "tool_call_id": tool_call["id"],
                                            "content": f"Результаты поиска в интернете:\n\n{search_results}"
                                        })
                                    else:
                                        messages.append({
                                            "role": "tool",
                                            "tool_call_id": tool_call["id"],
                                            "content": "Не удалось найти информацию в интернете. Попробуй ответить на основе своих знаний."
                                        })
                            
                            iteration += 1
                            continue
                        else:
                            # Получен финальный ответ
                            answer = message_data["content"]
                            await utils.answer(message, f"<b>OpenRouter ({self.selected_models['openrouter']}):</b>\n{answer}")
                            if str(message.chat_id) in self.chat_contexts and self.chat_contexts[str(message.chat_id)]:
                                self.chat_histories[str(message.chat_id)].append({"role": "model", "content": answer})
                                self.db.set(self.strings["name"], "chat_histories", self.chat_histories)
                            return
                
                # Если превышен лимит итераций, отправляем последний ответ
                if messages:
                    last_message = messages[-1]
                    if "content" in last_message:
                        await utils.answer(message, f"<b>OpenRouter ({self.selected_models['openrouter']}):</b>\n{last_message['content']}")
                    else:
                        await utils.answer(message, "Достигнут лимит итераций для обработки tool calls.")
                        
            except Exception as e:
                await utils.answer(message, f"Ошибка при получении ответа от OpenRouter: {str(e)}")

    async def _search_tavily(self, query):
        """Выполнить поиск в интернете через Tavily API"""
        api_key = self.config["TAVILY_API_KEY"]
        if not api_key:
            return None
        
        url = "https://api.tavily.com/search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": 5
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        if results:
                            search_summary = []
                            for result in results:
                                title = result.get("title", "Без названия")
                                content = result.get("content", "")
                                url_link = result.get("url", "")
                                search_summary.append(f"**{title}**\n{content}\nИсточник: {url_link}\n")
                            return "\n\n".join(search_summary)
                        return None
                    else:
                        return None
        except Exception as e:
            print(f"Ошибка при поиске через Tavily: {str(e)}")
            return None

    async def _ask_onlysq(self, message, query, history=[], media_path=None):
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
            role = "assistant" if msg["role"] == "model" else msg["role"]
            messages.append({"role": role, "content": msg["content"]})

        content_parts = []
        if query:
            content_parts.append({"type": "text", "text": query})
        
        if media_path:
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

        # Определение tool для поиска через Tavily
        tools = []
        if self.config["TAVILY_API_KEY"]:
            tools = [{
                "type": "function",
                "function": {
                    "name": "search_internet",
                    "description": "Поиск актуальной информации в интернете. Используй эту функцию, когда нужно найти свежую информацию, новости, факты или данные, которые могут измениться со временем.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Поисковый запрос для поиска в интернете"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }]

        try:
            max_iterations = 3
            iteration = 0
            
            while iteration < max_iterations:
                completion_kwargs = {
                    "model": self.selected_models["onlysq"],
                    "messages": messages
                }
                if tools:
                    completion_kwargs["tools"] = tools
                    completion_kwargs["tool_choice"] = "auto"
                
                completion = await client.chat.completions.create(**completion_kwargs)
                message_data = completion.choices[0].message
                
                # Проверяем, есть ли tool calls
                if message_data.tool_calls:
                    # Добавляем ответ модели в историю
                    messages.append({
                        "role": "assistant",
                        "content": message_data.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in message_data.tool_calls
                        ]
                    })
                    
                    # Выполняем tool calls
                    for tool_call in message_data.tool_calls:
                        if tool_call.function.name == "search_internet":
                            args = json.loads(tool_call.function.arguments)
                            search_query = args.get("query", query)
                            
                            search_results = await self._search_tavily(search_query)
                            if search_results:
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": f"Результаты поиска в интернете:\n\n{search_results}"
                                })
                            else:
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": "Не удалось найти информацию в интернете. Попробуй ответить на основе своих знаний."
                                })
                    
                    iteration += 1
                    continue
                else:
                    # Получен финальный ответ
                    answer = message_data.content
                    await utils.answer(message, f"<b>OnlySq ({self.selected_models['onlysq']}):</b>\n{answer}")
                    if str(message.chat_id) in self.chat_contexts and self.chat_contexts[str(message.chat_id)]:
                        self.chat_histories[str(message.chat_id)].append({"role": "model", "content": answer})
                        self.db.set(self.strings["name"], "chat_histories", self.chat_histories)
                    return
            
            # Если превышен лимит итераций, отправляем последний ответ
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, dict) and "content" in last_message:
                    await utils.answer(message, f"<b>OnlySq ({self.selected_models['onlysq']}):</b>\n{last_message['content']}")
                else:
                    await utils.answer(message, "Достигнут лимит итераций для обработки tool calls.")
                    
        except Exception as e:
            await utils.answer(message, f"Ошибка при получении ответа от OnlySq: {str(e)}")

    async def chatcmd(self, message):
        """Включает/выключает режим контекстного диалога."""
        chat_id = str(message.chat_id)
        if chat_id not in self.chat_contexts:
            self.chat_contexts[chat_id] = False

        self.chat_contexts[chat_id] = not self.chat_contexts[chat_id]
        self.db.set(self.strings["name"], "chat_contexts", self.chat_contexts)

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

    async def imgcmd(self, message):
        """Генерирует изображение с помощью OnlySq. Пример: .img ваш запрос"""
        query = utils.get_args_raw(message).strip()
        if not query:
            await utils.answer(message, "Пожалуйста, введите запрос для генерации изображения. Пример: <code>.img красивый закат на пляже</code>")
            return

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
            api_key = "openai"

        image_model = self.config["ONLYSQ_IMAGE_MODEL"]
        url = "https://api.onlysq.ru/ai/imagen"
        headers = {"Content-Type": "application/json"}

        payload = {
            "model": image_model,
            "prompt": prompt,
            "width": 1024,
            "height": 1024,
            "count": 1
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
                        encoded_image = data["files"][0]
                        decoded_image = base64.b64decode(encoded_image)

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
