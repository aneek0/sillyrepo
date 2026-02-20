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
import traceback

MAX_BUTTONS_PER_PAGE = 50
SUPPORTED_TEXT_MIMES = ['text/plain', 'text/html', 'text/css', 'text/javascript', 'application/json', 'application/x-python', 'text/x-python']

SEARCH_KEYWORDS = {
    "explicit": ["найти", "найди", "поиск", "search", "google", "гугл", "интернет", "web", "инфа", "инфу"],
    "time": ["время", "час", "дата", "сегодня", "завтра", "вчера", "год", "месяц"],
    "news": ["новости", "события", "произошло", "случилось", "news", "актуально"],
    "questions": ["кто", "что", "где", "когда", "почему", "как", "сколько", "чей", "какой"]
}

@loader.tds
class AzuAI(loader.Module):
    """Модуль для взаимодействия с нейросетями Gemini, OpenRouter и OnlySq с выбором модели через кнопки"""
    strings = {
        "name": "AzuAI",
        "cfg_openai_key": "API-ключ OpenAI",
        "openai_key_not_found": "API-ключ OpenAI не установлен"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "GEMINI_API_KEY", "", "API-ключ для Gemini AI",
            "OPENROUTER_API_KEY", "", "API-ключ для OpenRouter",
            "ONLYSQ_API_KEY", "OPENAI_KEY", lambda m: self.strings("cfg_openai_key", m),
            "TAVILY_API_KEY", "", "API-ключ для Tavily (поиск в интернете)",
            "DEFAULT_PROVIDER", 1, "Провайдер по умолчанию: 1 - Gemini, 2 - OpenRouter, 3 - OnlySq",
            "ONLYSQ_IMAGE_MODEL", "kandinsky", "Модель OnlySq для генерации изображений"
        )
        self.selected_models = {"gemini": "gemini-2.5-flash-preview-09-2025", "openrouter": "meta-llama/llama-3.1-8b-instruct:free", "onlysq": "gemini-3-flash"}
        self.model_lists = {"gemini": [], "openrouter": [], "onlysq": []}
        self.chat_contexts = {}
        self.chat_histories = {}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.chat_contexts = self.db.get(self.strings["name"], "chat_contexts", {})
        self.chat_histories = self.db.get(self.strings["name"], "chat_histories", {})
        await self._fetch_models()

    # ========== Методы загрузки моделей ==========
    
    async def _fetch_models(self):
        """Получить доступные модели для всех провайдеров"""
        await asyncio.gather(
            self._fetch_gemini_models(),
            self._fetch_openrouter_models(),
            self._fetch_onlysq_models(),
            return_exceptions=True
        )

    async def _fetch_gemini_models(self):
        """Загрузить модели Gemini"""
        if not self.config["GEMINI_API_KEY"]:
            print("API-ключ Gemini не установлен, пропуск получения моделей.")
            self.model_lists["gemini"] = []
            return

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.config['GEMINI_API_KEY']}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.model_lists["gemini"] = [
                            model["name"] for model in data.get("models", [])
                            if "generateContent" in model["supportedGenerationMethods"]
                        ]
                        print("Успешно получены модели Gemini")
                    else:
                        error_text = await response.text()
                        print(f"Ошибка получения моделей Gemini. Статус: {response.status}, Ответ: {error_text[:200]}...")
                        self.model_lists["gemini"] = []
        except aiohttp.ClientError as e:
            print(f"Ошибка сети при получении моделей Gemini: {str(e)}")
            self.model_lists["gemini"] = []
        except Exception as e:
            print(f"Непредвиденное исключение при получении моделей Gemini: {traceback.format_exc()}")
            self.model_lists["gemini"] = []

    async def _fetch_openrouter_models(self):
        """Загрузить модели OpenRouter"""
        if not self.config["OPENROUTER_API_KEY"]:
            print("API-ключ OpenRouter не установлен, пропуск получения моделей.")
            self.model_lists["openrouter"] = []
            return

        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {self.config['OPENROUTER_API_KEY']}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        all_models = [model["id"] for model in data.get("data", [])]
                        self.model_lists["openrouter"] = [
                            model_id for model_id in all_models
                            if any(model_id.startswith(prefix) for prefix in ['google/', 'deepseek/', 'meta-llama/'])
                        ]
                        print("Успешно получены все модели OpenRouter.")
                    else:
                        error_text = await response.text()
                        print(f"Ошибка получения моделей OpenRouter. Статус: {response.status}, Ответ: {error_text}")
                        self.model_lists["openrouter"] = []
        except aiohttp.ClientError as e:
            print(f"Ошибка сети при получении моделей OpenRouter: {str(e)}")
            self.model_lists["openrouter"] = []
        except Exception as e:
            print(f"Непредвиденное исключение при получении моделей OpenRouter: {traceback.format_exc()}")
            self.model_lists["openrouter"] = []

    async def _fetch_onlysq_models(self):
        """Загрузить модели OnlySq"""
        if self.config["ONLYSQ_API_KEY"] == "OPENAI_KEY":
            print("API-ключ OnlySq не установлен, пропуск загрузки моделей.")
            self.model_lists["onlysq"] = []
            return
        if not self.config["ONLYSQ_API_KEY"]:
            print("API-ключ OnlySq не установлен, пропуск загрузки моделей.")
            self.model_lists["onlysq"] = []
            return

        url = "https://api.onlysq.ru/ai/models"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.model_lists["onlysq"] = list(data.get("models", {}).keys())
                        print(f"Успешно получены модели OnlySq. Количество: {len(self.model_lists['onlysq'])}")
                    else:
                        error_text = await response.text()
                        print(f"Ошибка получения моделей OnlySq. Статус: {response.status}, Ответ: {error_text}")
                        self.model_lists["onlysq"] = []
        except aiohttp.ClientError as e:
            print(f"Ошибка сети при получении моделей OnlySq: {str(e)}")
            self.model_lists["onlysq"] = []
        except Exception as e:
            print(f"Непредвиденное исключение при получении моделей OnlySq: {traceback.format_exc()}")
            self.model_lists["onlysq"] = []

    # ========== Методы настройки ==========

    async def aicfgcmd(self, message):
        """⚙️ Настроить провайдера и модель"""
        await self.inline.form(
            text="⚙️ <b>Настройки AIModule:</b>\n\nAPI-ключи устанавливаются в конфигурации модуля.",
            message=message,
            reply_markup=[
                [{"text": "Выбор провайдера", "callback": self._show_settings_menu, "args": ("providers",)}],
                [{"text": "Выбор модели", "callback": self._show_settings_menu, "args": ("models_service",)}]
            ]
        )

    async def _show_settings_menu(self, call, menu_type):
        """Показать меню настроек"""
        if menu_type == "main":
            text = "⚙️ <b>Настройки AIModule:</b>\n\nAPI-ключи устанавливаются в конфигурации модуля."
            reply_markup = [
                [{"text": "Выбор провайдера", "callback": self._show_settings_menu, "args": ("providers",)}],
                [{"text": "Выбор модели", "callback": self._show_settings_menu, "args": ("models_service",)}]
            ]
        elif menu_type == "providers":
            text, reply_markup = self._build_providers_menu()
        elif menu_type == "models_service":
            text = "🔧 <b>Выберите сервис для выбора модели:</b>"
            reply_markup = [
                [{"text": "Gemini", "callback": self._show_models, "args": ("gemini",)}],
                [{"text": "OpenRouter", "callback": self._show_models, "args": ("openrouter",)}],
                [{"text": "OnlySq", "callback": self._show_models, "args": ("onlysq",)}],
                [{"text": "⬅️ Назад", "callback": self._show_settings_menu, "args": ("main",)}]
            ]
        else:
            return

        await call.edit(text=text, reply_markup=reply_markup)

    def _build_providers_menu(self):
        """Построить меню выбора провайдера"""
        current_provider = self.config["DEFAULT_PROVIDER"]
        provider_map = {1: "Gemini", 2: "OpenRouter", 3: "OnlySq"}
        
        def get_provider_button(provider_id, provider_name):
            text = provider_name + ("🟣" if current_provider == provider_id else "")
            return {"text": text, "callback": self._set_provider, "args": (provider_id,)}

        text = "🔧 <b>Выберите провайдера по умолчанию:</b>"
        reply_markup = [
            [get_provider_button(pid, pname)] for pid, pname in provider_map.items()
        ] + [[{"text": "⬅️ Назад", "callback": self._show_settings_menu, "args": ("main",)}]]
        
        return text, reply_markup

    async def _set_provider(self, call, provider_id):
        """Установить провайдера по умолчанию"""
        self.config["DEFAULT_PROVIDER"] = provider_id
        provider_map = {1: "Gemini", 2: "OpenRouter", 3: "OnlySq"}
        provider_name = provider_map.get(provider_id, "Unknown")
        
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

        limit, total_pages, current_models = self._calculate_pagination(models, page)
        buttons = self._build_model_buttons(current_models, service, page, total_pages)
        
        await call.edit(
            f"🔧 <b>Выберите модель для {service}:</b>",
            reply_markup=buttons
        )

    def _calculate_pagination(self, models, page):
        """Рассчитать пагинацию для списка моделей"""
        total_models = len(models)
        
        if total_models <= MAX_BUTTONS_PER_PAGE:
            limit = total_models
        else:
            num_pages = (total_models + MAX_BUTTONS_PER_PAGE - 1) // MAX_BUTTONS_PER_PAGE
            limit = (total_models + num_pages - 1) // num_pages if num_pages > 0 else 1

        total_pages = (total_models + limit - 1) // limit if limit > 0 else 1
        page = max(0, min(page, total_pages - 1))
        
        offset = page * limit
        current_models = models[offset:offset + limit]
        
        return limit, total_pages, current_models

    def _build_model_buttons(self, models, service, page, total_pages):
        """Построить кнопки для выбора моделей"""
        selected_model = self.selected_models.get(service)
        buttons = []
        
        for model in models:
            button_text = model + ("🟣" if model == selected_model else "")
            buttons.append([{"text": button_text, "callback": self._set_model, "args": (service, model, page)}])
        
        if total_pages > 1:
            nav = []
            if page > 0:
                nav.append({"text": "⬅️", "callback": self._show_models, "args": (service, page - 1)})
            nav.append({"text": f"{page + 1}/{total_pages}", "callback": self._show_models, "args": (service, page)})
            if page < total_pages - 1:
                nav.append({"text": "➡️", "callback": self._show_models, "args": (service, page + 1)})
            buttons.append(nav)

        buttons.append([{"text": "⬅️ Назад", "callback": self._show_settings_menu, "args": ("models_service",)}])
        return buttons

    async def _set_model(self, call, service, model, page=0):
        """Установить выбранную модель"""
        self.selected_models[service] = model
        await call.edit(f"✅ <b>Модель выбрана:</b> {model}")
        await asyncio.sleep(1)
        await self._show_models(call, service, page)

    # ========== Основные команды ==========

    async def askcmd(self, message):
        """Задать вопрос ИИ"""
        query, media_path = await self._extract_query_and_media(message)
        
        if not query and not media_path:
            await utils.answer(message, "Пожалуйста, введите запрос или ответьте на сообщение с текстом, фото или видео. Пример: <code>.ask ваш вопрос</code>")
            return

        service = self._get_service_name()
        chat_id = str(message.chat_id)
        is_context_enabled = self.chat_contexts.get(chat_id, False)
        history = self.chat_histories.get(chat_id, []) if is_context_enabled else []

        try:
            if service == "gemini":
                await self._ask_gemini(message, query, history, media_path, chat_id)
            elif service == "openrouter":
                await self._ask_openrouter(message, query, history, media_path, chat_id)
            elif service == "onlysq":
                await self._ask_onlysq(message, query, history, media_path, chat_id)
        finally:
            if media_path and os.path.exists(media_path):
                os.remove(media_path)

    def _get_service_name(self):
        """Получить имя сервиса по провайдеру"""
        provider_map = {1: "gemini", 2: "openrouter", 3: "onlysq"}
        return provider_map.get(self.config["DEFAULT_PROVIDER"], "onlysq")

    async def _extract_query_and_media(self, message):
        """Извлечь запрос и медиа из сообщения"""
        query = utils.get_args_raw(message).strip()
        media_path = None

        if not message.is_reply:
            return query, media_path

        try:
            reply_message = await message.get_reply_message()
            if not reply_message:
                return query, media_path

            # Обработка текста
            if reply_message.text:
                query = reply_message.text.strip() if not query else f"{query}\n{reply_message.text.strip()}"

            # Обработка изображений
            if reply_message.photo or (reply_message.document and 
                                      reply_message.document.mime_type and 
                                      reply_message.document.mime_type.startswith('image/')):
                processing_message = await utils.answer(message, "🧠 Обнаружено фото/изображение. Загрузка...")
                try:
                    media_path = await reply_message.download_media(file=tempfile.gettempdir())
                    await processing_message.edit("🧠 Изображение загружено. Обработка запроса...")
                except Exception as e:
                    await utils.answer(message, f"Ошибка при загрузке изображения: {str(e)}")
                    return None, None

            # Обработка текстовых файлов
            elif reply_message.document:
                media_path = await self._handle_text_file(reply_message, message, query)
                if media_path is False:  # Ошибка обработки
                    return None, None
                query = media_path if isinstance(media_path, str) else query
                media_path = None

        except Exception as e:
            print(f"Ошибка в _extract_query_and_media: {traceback.format_exc()}")
            await utils.answer(message, f"Ошибка при получении текста из ответа или загрузке медиа: {str(e)}")
            return None, None

        return query, media_path

    async def _handle_text_file(self, reply_message, message, query):
        """Обработать текстовый файл"""
        mime_type = reply_message.document.mime_type
        if not mime_type or not any(mime_type.startswith(prefix) or mime_type == prefix 
                                   for prefix in SUPPORTED_TEXT_MIMES):
            await utils.answer(message, f"Примечание: Прямая обработка файлов типа '{mime_type}' не поддерживается.")
            try:
                temp_file = await reply_message.download_media(file=tempfile.gettempdir())
                os.remove(temp_file)
            except Exception:
                pass
            return False

        processing_message = await utils.answer(message, f"🧠 Обнаружен текстовый файл ({mime_type}). Загрузка и чтение...")
        try:
            temp_file_path = await reply_message.download_media(file=tempfile.gettempdir())
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            os.remove(temp_file_path)
            
            await processing_message.edit("🧠 Файл прочитан. Обработка запроса...")
            return file_content if not query else f"{query}\n\n--- Содержимое файла ---\n{file_content}"
        except Exception as e:
            await utils.answer(message, f"Ошибка при загрузке или чтении файла: {str(e)}")
            return False

    # ========== Вспомогательные методы ==========

    def _save_chat_history(self, chat_id, user_content, answer):
        """Сохранить историю диалога"""
        if chat_id not in self.chat_histories:
            self.chat_histories[chat_id] = []
        if user_content:
            self.chat_histories[chat_id].append({"role": "user", "content": user_content})
            self.chat_histories[chat_id].append({"role": "model", "content": answer})
            self.db.set(self.strings["name"], "chat_histories", self.chat_histories)

    def _get_user_content(self, query, media_path):
        """Получить контент пользователя для истории"""
        return query if query else ("[изображение]" if media_path else "")

    def _should_search_for_gemini(self, query):
        """Определить, нужен ли поиск для Gemini модели"""
        if not query:
            return False

        query_lower = query.lower()
        
        explicit_search = any(word in query_lower for word in SEARCH_KEYWORDS["explicit"])
        time_indicators = any(word in query_lower for word in SEARCH_KEYWORDS["time"])
        news_events = any(word in query_lower for word in SEARCH_KEYWORDS["news"])
        is_question = any(word in query_lower for word in SEARCH_KEYWORDS["questions"])

        return explicit_search or time_indicators or news_events or (is_question and len(query.split()) > 3)

    def _create_search_tool(self):
        """Создать определение tool для поиска"""
        return [{
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

    async def _search_tavily(self, query):
        """Выполнить поиск в интернете через Tavily API"""
        if not self.config["TAVILY_API_KEY"]:
            return None

        url = "https://api.tavily.com/search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": self.config["TAVILY_API_KEY"],
            "query": query,
            "search_depth": "basic",
            "max_results": 15
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
        except Exception as e:
            print(f"Ошибка при поиске через Tavily: {str(e)}")
        
        return None

    # ========== Методы для работы с провайдерами ==========

    async def _ask_gemini(self, message, query, history, media_path, chat_id):
        """Запрос к Gemini API"""
        api_key = self.config["GEMINI_API_KEY"]
        if not api_key:
            await utils.answer(message, "API-ключ для Gemini не установлен.")
            return

        model_id = self.selected_models['gemini'].replace('models/', '')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}

        contents = [{"role": msg["role"], "parts": [{"text": msg["content"]}]} for msg in history]
        
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
                    await utils.answer(message, "Неподдерживаемый тип медиафайла для Gemini (не изображение).")
            except Exception as e:
                await utils.answer(message, f"Ошибка при кодировании медиафайла: {str(e)}")
                return

        if not parts:
            await utils.answer(message, "Не удалось сформировать части запроса для Gemini.")
            return

        contents.append({"role": "user", "parts": parts})
        payload = {"contents": contents, "tools": [{"googleSearch": {}}]}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        await utils.answer(message, f"Ошибка от Gemini: Status {response.status}: {error_text[:200]}...")
                        return

                    data = await response.json()
                    answer = self._parse_gemini_response(data, message)
                    
                    if answer:
                        await utils.answer(message, f"<b>Gemini ({self.selected_models['gemini']}):</b>\n{answer}")
                        if chat_id in self.chat_contexts and self.chat_contexts[chat_id]:
                            user_content = self._get_user_content(query, media_path)
                            self._save_chat_history(chat_id, user_content, answer)
        except aiohttp.ClientError as e:
            await utils.answer(message, f"Ошибка сети при запросе к Gemini: {str(e)}")
        except Exception as e:
            print(f"Критическая ошибка в _ask_gemini: {traceback.format_exc()}")
            await utils.answer(message, f"Ошибка при получении ответа от Gemini: {str(e)}")

    def _parse_gemini_response(self, data, message):
        """Парсить ответ от Gemini API"""
        if not data or "candidates" not in data or not data["candidates"]:
            if data and "promptFeedback" in data and data["promptFeedback"].get("blockReason"):
                block_reason = data["promptFeedback"]["blockReason"]
                asyncio.create_task(utils.answer(message, f"⚠️ Запрос заблокирован: {block_reason}"))
            return None

        answer_parts = []
        candidate = data["candidates"][0]
        
        for part in candidate["content"]["parts"]:
            if "text" in part:
                answer_parts.append(part["text"])
            if "groundingAttributions" in part:
                for attribution in part["groundingAttributions"]:
                    if "uri" in attribution:
                        answer_parts.append(f" [[{attribution.get('title', 'ссылка')}]]({'uri'})")

        answer = "".join(answer_parts)
        
        if not answer:
            if candidate.get("finishReason") == "SAFETY" or candidate.get("blockReason"):
                block_reason = candidate.get("blockReason") or candidate.get("finishReason")
                asyncio.create_task(utils.answer(message, f"⚠️ Запрос заблокирован: {block_reason}"))
            else:
                asyncio.create_task(utils.answer(message, "Получен пустой ответ от Gemini API"))
        
        return answer

    async def _ask_openrouter(self, message, query, history, media_path, chat_id):
        """Запрос к OpenRouter API"""
        api_key = self.config["OPENROUTER_API_KEY"]
        if not api_key:
            await utils.answer(message, "API-ключ для OpenRouter не установлен.")
            return

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = self._convert_history_to_messages(history)
        if media_path:
            await utils.answer(message, "Примечание: OpenRouter не поддерживает прямую мультимодальную обработку изображений.")
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
                    if str(message.chat_id) in self.chat_contexts and self.chat_contexts[str(message.chat_id)]:
                        self.chat_histories[str(message.chat_id)].append({"role": "model", "content": answer})
                        self.db.set(self.strings["name"], "chat_histories", self.chat_histories)
            except aiohttp.ClientError as e:
                await utils.answer(message, f"Ошибка сети при запросе к OpenRouter: {str(e)}")
            except Exception as e:
                print(f"Критическая ошибка в _ask_openrouter: {traceback.format_exc()}")
                await utils.answer(message, f"Ошибка при получении ответа от OpenRouter: {str(e)}")

    async def _ask_onlysq(self, message, query, history, media_path, chat_id):
        api_key = self.config["ONLYSQ_API_KEY"]
        if api_key == "OPENAI_KEY":
            await utils.answer(message, self.strings("openai_key_not_found", message))
            return
        if not api_key:
            await utils.answer(message, "API-ключ для OnlySq не установлен.")
            return

        client = AsyncOpenAI(
            base_url="https://api.onlysq.ru/ai/openai",
            api_key=api_key,
        )

        messages = self._convert_history_to_messages(history)
        messages = await self._prepare_onlysq_messages(messages, query, media_path, message)
        
        if not messages:
            return

        tools = []
        model_name = self.selected_models["onlysq"].lower()
        is_gemini_model = "gemini" in model_name

        if self.config["TAVILY_API_KEY"]:
            if is_gemini_model:
                # Для Gemini моделей: автоматический поиск
                if self._should_search_for_gemini(query):
                    search_results = await self._search_tavily(query)
                    if search_results:
                        search_context = f"\n\n[Актуальная информация из интернета по вашему запросу:\n{search_results}\nИспользуйте эту информацию для ответа.]"
                        query = query + search_context
                        if messages and messages[-1]["role"] == "user":
                            if isinstance(messages[-1]["content"], str):
                                messages[-1]["content"] = query
                            elif isinstance(messages[-1]["content"], list):
                                for part in messages[-1]["content"]:
                                    if part.get("type") == "text":
                                        part["text"] = query
                                        break
            else:
                # Для не-Gemini моделей: tool calling
                tools = self._create_search_tool()

        try:
            # Inline processing instead of missing _process_onlysq_completion
            completion = await client.chat.completions.create(
                model=self.selected_models["onlysq"],
                messages=messages,
                tools=tools if tools else None
            )
            
            # Handle potential tool calls or direct content
            response_message = completion.choices[0].message
            if response_message.tool_calls and not is_gemini_model:
                # Basic tool call handling (Tavily search)
                tool_call = response_message.tool_calls[0]
                if tool_call.function.name == "search_internet":
                    import json
                    args = json.loads(tool_call.function.arguments)
                    search_results = await self._search_tavily(args.get("query"))
                    if search_results:
                        messages.append(response_message)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": "search_internet",
                            "content": search_results
                        })
                        completion = await client.chat.completions.create(
                            model=self.selected_models["onlysq"],
                            messages=messages
                        )
                        answer = completion.choices[0].message.content
                    else:
                        answer = response_message.content
                else:
                    answer = response_message.content
            else:
                answer = response_message.content

            if answer:
                await utils.answer(message, f"<b>OnlySq ({self.selected_models['onlysq']}):</b>\n{answer}")
                if chat_id in self.chat_contexts and self.chat_contexts[chat_id]:
                    user_content = self._get_user_content(query, media_path)
                    self._save_chat_history(chat_id, user_content, answer)
        except Exception as e:
            error_details = f"{str(e)}\n\nТип ошибки: {type(e).__name__}"
            if len(error_details) > 500:
                error_details = error_details[:500] + "..."
            await utils.answer(message, f"❌ Ошибка при получении ответа от OnlySq:\n{error_details}")
            print(f"OnlySq error traceback:\n{traceback.format_exc()}")

    def _convert_history_to_messages(self, history):
        """Конвертировать историю в формат messages"""
        return [
            {"role": "assistant" if msg["role"] == "model" else msg["role"], "content": msg["content"]}
            for msg in history
        ]

    async def _prepare_onlysq_messages(self, messages, query, media_path, message):
        """Подготовить сообщения для OnlySq"""
        content_parts = []
        if media_path:
            if query:
                content_parts.append({"type": "text", "text": query})
            
            try:
                with open(media_path, "rb") as f:
                    encoded_media = base64.b64encode(f.read()).decode('utf-8')
                mime_type, _ = mimetypes.guess_type(media_path)
                if mime_type and mime_type.startswith('image/'):
                    content_parts.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded_media}"}})
                else:
                    await utils.answer(message, "OnlySq: Неподдерживаемый тип медиафайла (не изображение).")
                    if query:
                        messages.append({"role": "user", "content": query})
                        return messages
                    await utils.answer(message, "OnlySq: Не удалось сформировать запрос.")
                    return []
            except Exception as e:
                await utils.answer(message, f"Ошибка при кодировании медиафайла для OnlySq: {str(e)}")
                return []

        if content_parts:
            messages.append({"role": "user", "content": content_parts})
        elif query:
            messages.append({"role": "user", "content": query})
        else:
            await utils.answer(message, "OnlySq: Не удалось сформировать части запроса (нет текста или медиа).")
            return []

        return messages

    async def chatcmd(self, message):
        """Включает/выключает режим контекстного диалога"""
        chat_id = str(message.chat_id)
        if chat_id not in self.chat_contexts:
            self.chat_contexts[chat_id] = False

        self.chat_contexts[chat_id] = not self.chat_contexts[chat_id]
        self.db.set(self.strings["name"], "chat_contexts", self.chat_contexts)

        status = "включен" if self.chat_contexts[chat_id] else "выключен"
        await utils.answer(message, f"Режим контекстного диалога для этого чата {status}.")

    async def clearchatcmd(self, message):
        """Очищает историю контекстного диалога для текущего чата"""
        chat_id = str(message.chat_id)
        if chat_id in self.chat_histories:
            del self.chat_histories[chat_id]
            self.db.set(self.strings["name"], "chat_histories", self.chat_histories)
            await utils.answer(message, "История диалога очищена.")
        else:
            await utils.answer(message, "История диалога уже пуста.")

    # ========== Генерация изображений ==========

    async def imgcmd(self, message):
        """Генерирует изображение с помощью OnlySq"""
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
        """Генерирует изображение с помощью OnlySq API"""
        api_key = self.config["ONLYSQ_API_KEY"]
        if api_key == "OPENAI_KEY":
            await utils.answer(message, self.strings("openai_key_not_found", message))
            return None
        if not api_key:
            await utils.answer(message, "API-ключ для OnlySq не установлен.")
            return None
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
                        await utils.answer(message, f"Ошибка при генерации изображения: Status {response.status}: {error_text[:200]}...")
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
        except aiohttp.ClientError as e:
            await utils.answer(message, f"Ошибка сети при запросе к OnlySq Imagen API: {str(e)}")
            return None
        except Exception as e:
            print(f"Критическая ошибка в _generate_image_onlysq: {traceback.format_exc()}")
            await utils.answer(message, f"Непредвиденная ошибка при генерации изображения: {str(e)}")
            return None
