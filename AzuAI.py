import aiohttp
from .. import loader, utils
from telethon import events

@loader.tds
class AzuAI(loader.Module):
    """Модуль для взаимодействия с нейросетями Gemini и OpenRouter с выбором модели через кнопки"""
    strings = {
        "name": "AzuAI"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "GEMINI_API_KEY", "", "API-ключ для Gemini AI",
            "OPENROUTER_API_KEY", "", "API-ключ для OpenRouter",
            "DEFAULT_PROVIDER", 1, "Провайдер по умолчанию: 1 - Gemini, 2 - OpenRouter"
        )
        self.selected_models = {"gemini": "gemini-2.5-flash-preview-05-20", "openrouter": "meta-llama/llama-3.1-8b-instruct:free"}
        self.model_lists = {"gemini": [], "openrouter": []}
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
        """Получить доступные модели Gemini и OpenRouter"""
        # Gemini
        if self.config["GEMINI_API_KEY"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.config['GEMINI_API_KEY']}"
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.model_lists["gemini"] = [model["name"] for model in data.get("models", [])]
                            # Добавим лог или сообщение об успехе получения моделей
                            print("Успешно получены модели Gemini")
                            # Добавим вывод тела ответа для отладки
                            print(f"Тело ответа Gemini Models (status 200): {data}")
                        else:
                            # Добавим более детальное сообщение об ошибке при получении моделей
                            error_text = await response.text()
                            print(f"Ошибка получения моделей Gemini. Статус: {response.status}, Ответ: {error_text[:200]}...")
                            self.model_lists["gemini"] = []
                except Exception as e:
                    # Добавим детальное сообщение об ошибке при выполнении запроса
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
                            # Собираем все модели OpenRouter
                            all_openrouter_models = [model["id"] for model in data.get("data", [])]
                            # Фильтруем модели по указанным префиксам
                            self.model_lists["openrouter"] = [
                                model_id for model_id in all_openrouter_models
                                if model_id.startswith('google/') or model_id.startswith('deepseek/') or model_id.startswith('meta-llama/')
                            ]
                            print("Успешно получены все модели OpenRouter.")
                            print(f"Общее количество моделей до фильтрации: {len(all_openrouter_models)}")
                            print(f"Количество моделей OpenRouter после фильтрации: {len(self.model_lists['openrouter'])}")
                            # Выводим список отфильтрованных моделей в консоль для диагностики
                            print("Список отфильтрованных моделей OpenRouter:")
                            for model_id in self.model_lists["openrouter"]:
                                print(f"- {model_id}")
                            print(f"Тело ответа OpenRouter Models (status 200): {data}")
                        else:
                            error_text = await response.text()
                            # Улучшенное логирование ошибки для OpenRouter
                            print(f"Ошибка получения моделей OpenRouter. Статус: {response.status}, Ответ: {error_text}")
                            self.model_lists["openrouter"] = []
                except Exception as e:
                    # Улучшенное логирование исключения для OpenRouter
                    print(f"Исключение при получении моделей OpenRouter: {str(e)}")
                    self.model_lists["openrouter"] = []
        else:
            print("API-ключ OpenRouter не установлен, пропуск получения моделей.")
            self.model_lists["openrouter"] = []

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
                [{"text": "Выбор провайдера", "callback": self._show_providers}],
                [{"text": "Выбор модели", "callback": self._show_service_for_model}],
                [{"text": "❌ Закрыть", "callback": self._close_form}]
            ]
        )

    async def _show_providers(self, call):
        """Показать кнопки для выбора провайдера"""
        await call.edit(
            "🔧 <b>Выберите провайдера по умолчанию:</b>",
            reply_markup=[
                [{"text": "Gemini", "callback": self._set_provider, "args": (1,)}],
                [{"text": "OpenRouter", "callback": self._set_provider, "args": (2,)}],
                [{"text": "⬅️ Назад", "callback": self._back_to_aicfg}, {"text": "❌ Закрыть", "callback": self._close_form}]
            ]
        )

    async def _set_provider(self, call, provider_id):
        """Установить провайдера по умолчанию из инлайн-кнопки"""
        self.config["DEFAULT_PROVIDER"] = provider_id
        provider_name = "Gemini" if provider_id == 1 else "OpenRouter"
        await call.edit(f"Провайдер по умолчанию установлен: {provider_name}")
        # Возвращаемся в главное меню aicfg, редактируя текущее сообщение
        await call.edit(
            text="⚙️ <b>Настройки AIModule:</b>\n\nAPI-ключи устанавливаются в конфигурации модуля (через файл или команды setkey, если доступны).",
            reply_markup=[
                [{"text": "Выбор провайдера", "callback": self._show_providers}],
                [{"text": "Выбор модели", "callback": self._show_service_for_model}],
                [{"text": "❌ Закрыть", "callback": self._close_form}]
            ]
        )

    async def _show_service_for_model(self, call):
        """Показать кнопки для выбора сервиса для выбора модели"""
        await call.edit(
            "🔧 <b>Выберите сервис для выбора модели:</b>",
            reply_markup=[
                [{"text": "Gemini", "callback": self._show_models, "args": ("gemini",)}],
                [{"text": "OpenRouter", "callback": self._show_models, "args": ("openrouter",)}],
                [{"text": "⬅️ Назад", "callback": self._back_to_aicfg}, {"text": "❌ Закрыть", "callback": self._close_form}]
            ]
        )

    async def _show_models(self, call, service):
        """Показать инлайн-кнопки для выбора модели"""
        models = self.model_lists.get(service, [])
        if not models:
            # Возвращаем пользователя в меню выбора сервиса для модели, если моделей нет
            await call.edit(f"⚠️ <b>Нет доступных моделей для {service}.</b> Проверьте API-ключ и попробуйте снова.")
            # Используем call.inline_message для возврата в предыдущее меню с кнопками
            await self._show_service_for_model(call)
            return
        buttons = []
        for model in models:
            buttons.append([{"text": model, "callback": self._set_model, "args": (service, model)}])
        buttons.append([
            {"text": "⬅️ Назад", "callback": self._show_service_for_model},
            {"text": "❌ Закрыть", "callback": self._close_form}
        ]) # Кнопки Назад и Закрыть в одном ряду
        await call.edit(
            f"🔧 <b>Выберите модель для {service}:</b>",
            reply_markup=buttons
        )

    async def _set_model(self, call, service, model):
        """Установить выбранную модель из инлайн-кнопки"""
        self.selected_models[service] = model
        await call.edit(f"✅ <b>Модель выбрана:</b> {model}")
        # Возвращаемся в меню выбора сервиса для модели, редактируя текущее сообщение
        await call.edit(
            "🔧 <b>Выберите сервис для выбора модели:</b>",
            reply_markup=[
                [{"text": "Gemini", "callback": self._show_models, "args": ("gemini",)}],
                [{"text": "OpenRouter", "callback": self._show_models, "args": ("openrouter",)}],
                [{"text": "⬅️ Назад", "callback": self._back_to_aicfg}],
                [{"text": "❌ Закрыть", "callback": self._close_form}]
            ]
        )

    async def _back_to_aicfg(self, call):
        """Вернуться в главное меню настроек AIModule"""
        # Возвращаемся в главное меню aicfg, редактируя текущее сообщение
        await call.edit(
            text="⚙️ <b>Настройки AIModule:</b>\n\nAPI-ключи устанавливаются в конфигурации модуля (через файл или команды setkey, если доступны).",
            reply_markup=[
                [{"text": "Выбор провайдера", "callback": self._show_providers}],
                [{"text": "Выбор модели", "callback": self._show_service_for_model}],
                [{"text": "❌ Закрыть", "callback": self._close_form}]
            ]
        )

    async def _close_form(self, call):
        """Закрыть инлайн-форму (удалить сообщение с кнопками)"""
        await call.delete()

    async def askcmd(self, message):
        """Задать вопрос ИИ. Пример: .ask ваш вопрос или ответить на сообщение с .ask"""
        query = utils.get_args_raw(message).strip()

        # Проверяем, является ли сообщение ответом
        if not query and message.is_reply:
            try:
                # Получаем оригинальное сообщение, на которое ответили
                reply_message = await message.get_reply_message()
                if reply_message and reply_message.text:
                    query = reply_message.text.strip()
            except Exception as e:
                await utils.answer(message, f"Ошибка при получении текста из ответа: {str(e)}")
                return

        if not query:
            await utils.answer(message, "Пожалуйста, введите запрос или ответьте на сообщение. Пример: <code>.ask ваш вопрос</code>")
            return
        service = "gemini" if self.config["DEFAULT_PROVIDER"] == 1 else "openrouter"

        # Отправляем сообщение о начале обработки запроса
        # processing_message = await utils.answer(message, "🧠 Обработка запроса...") # Удалена, так как не работает удаление

        chat_id = str(message.chat_id)
        is_context_enabled = self.chat_contexts.get(chat_id, False)
        history = self.chat_histories.get(chat_id, [])

        if is_context_enabled:
            # Добавляем текущий запрос пользователя в историю для контекста
            history.append({"role": "user", "content": query})
            self.chat_histories[chat_id] = history

        # Логика поиска удалена, т.к. Gemini сам решает использовать ли Grounding (поиск)

        ai_response_message = None
        if service == "gemini":
            ai_response_message = await self._ask_gemini(message, query, history if is_context_enabled else []) # Передаем историю только если контекст включен
        else:
            ai_response_message = await self._ask_openrouter(message, query, history if is_context_enabled else []) # Передаем историю только если контекст включен

        # Удаляем сообщение "Обработка запроса..."
        # if processing_message:
        #     await processing_message.delete() # Удалена, так как не работает удаление

        # После ответа ИИ, если контекст включен, добавляем кнопку очистки диалога
        # if is_context_enabled and ai_response_message:
        #     await self.inline.form(
        #         text=ai_response_message.text, # Используем текст ответа ИИ
        #         message=ai_response_message, # Привязываем к сообщению с ответом ИИ
        #         reply_markup=[[{"text": "🗑️ Очистить диалог", "callback": self._clear_chat_history_callback}]],
        #         disable_security=True # Разрешаем без безопасности для работы с кнопками
        #     )

    async def _ask_gemini(self, message, query, history=[]): # Добавляем history как аргумент
        api_key = self.config["GEMINI_API_KEY"]
        if not api_key:
            await utils.answer(message, "API-ключ для Gemini не установлен. Используйте <code>.setkey {{gemini,openrouter}} &lt;ваш_ключ&gt;</code>.")
            return

        # Взаимодействие с Gemini API через HTTP с использованием Grounding
        model_id = self.selected_models['gemini'].replace('models/', '')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}

        # Формируем список сообщений для контекста
        contents = []
        for msg in history:
            contents.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})
        contents.append({"role": "user", "parts": [{"text": query}]}) # Добавляем текущий запрос пользователя

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
                                             answer_parts.append(f" [[{attribution.get('title', 'ссылка')}]]({attribution['uri']})")

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
                             # return await utils.answer(message, f"<b>Gemini ({self.selected_models['gemini']}):</b>\n{answer}") # Возвращаем сообщение с ответом

                    elif data and "promptFeedback" in data and data["promptFeedback"].get("blockReason"):
                         block_reason = data["promptFeedback"]["blockReason"]
                         await utils.answer(message, f"⚠️ Запрос к Gemini заблокирован: {block_reason}")
                    else:
                         await utils.answer(message, "Ошибка при получении ответа от Gemini (HTTP): Неожиданный формат ответа от API")

            except Exception as e:
                await utils.answer(message, f"Ошибка при получении ответа от Gemini (HTTP): {str(e)}")

    async def _ask_openrouter(self, message, query, history=[]): # Добавляем history как аргумент
        api_key = self.config["OPENROUTER_API_KEY"]
        if not api_key:
            await utils.answer(message, "API-ключ для OpenRouter не установлен. Используйте <code>.setkey {{gemini,openrouter}} &lt;ваш_ключ&gt;</code>.")
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
        messages.append({"role": "user", "content": query}) # Добавляем текущий запрос пользователя

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
                    # return await utils.answer(message, f"<b>OpenRouter ({self.selected_models['openrouter']}):</b>\n{answer}") # Возвращаем сообщение с ответом
            except Exception as e:
                await utils.answer(message, f"Ошибка при получении ответа от OpenRouter: {str(e)}")

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