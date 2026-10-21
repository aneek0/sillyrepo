# meta developer: @aneek0

import asyncio
import base64
import json
import logging
import os
import re
import urllib.error
import urllib.request
from openai import AsyncOpenAI

from .. import loader, utils
from ..inline.types import InlineCall


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Answer in GitHub-flavored Markdown. Never wrap the whole answer in a code block "
    "and never output HTML tags. Use the web search tool when it would improve the answer."
)

MAX_BUTTONS_PER_PAGE = 90
REQUEST_TIMEOUT = 120
SEARCH_TIMEOUT = 45
FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search"
EXCERPT_CHARS = 6000

_OBVIOUSLY_TEXT_ONLY = (
    "qwq", "whisper",
    "tts", "embedding", "davinci", "babbage", "ada",
)

_vision_cache: dict[str, bool] = {}


def _firecrawl_search(query: str, api_key: str) -> list[dict]:
    """Blocking Firecrawl /v2/search call; run it via asyncio.to_thread."""
    payload = {
        "query": query,
        "limit": 5,
        "sources": ["web"],
        "scrapeOptions": {"formats": [{"type": "markdown"}]},
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        FIRECRAWL_SEARCH_URL,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=SEARCH_TIMEOUT) as response:
        data = json.loads(response.read().decode())

    results = (data.get("data") or {}).get("web") or []
    return results if isinstance(results, list) else []


def _topic_id(message) -> int | None:
    """Forum topic id of the message, so bot replies stay in the same topic."""
    reply_to = getattr(message, "reply_to", None)
    if reply_to is None or not getattr(reply_to, "forum_topic", False):
        return None
    return reply_to.reply_to_top_id or reply_to.reply_to_msg_id


def _strip_fences(text: str) -> str:
    """Models sometimes wrap the whole answer in a ```lang ... ``` block."""
    match = re.fullmatch(r"\s*```(?:html|markdown|md)?[ \t]*\n(.*?)\n?```\s*", text, re.DOTALL)
    return match.group(1) if match else text

def _message_text(msg) -> str:
    """Visible answer text of a completion message.

    Reasoning models (glm-5.3, o-series) sometimes return 200 with an empty
    ``content`` and the text only in ``reasoning_content``. Take whichever
    field carries text instead of rendering an empty answer.
    """
    return (msg.content or "").strip() or (
        getattr(msg, "reasoning_content", None) or ""
    ).strip()

def _get_context_dir() -> str:
    # External modules are exec'd from source, so __file__ is undefined here;
    # the loader module's own path gives us the install root in both forks
    loader_file = getattr(loader, "__file__", None)
    root = (
        os.path.dirname(os.path.dirname(os.path.abspath(loader_file)))
        if loader_file
        else os.path.join(os.path.expanduser("~"), ".heroku")
    )
    base = os.path.join(root, "azuai_contexts")
    legacy = os.path.join(os.path.expanduser("~"), ".hikka", "azuai_contexts")
    if not os.path.isdir(base) and os.path.isdir(legacy):
        os.replace(legacy, base)
    os.makedirs(base, exist_ok=True)
    return base


def _context_path(chat_id: int) -> str:
    return os.path.join(_get_context_dir(), f"{chat_id}.json")


def _load_context(chat_id: int) -> dict:
    path = _context_path(chat_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"enabled": False, "history": []}


def _save_context(chat_id: int, data: dict):
    path = _context_path(chat_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _delete_context(chat_id: int):
    path = _context_path(chat_id)
    if os.path.exists(path):
        os.remove(path)


@loader.tds
class AzuAIMod(loader.Module):
    """Общение с AI через OpenAI-Compatible API"""

    strings = {
        "name": "AzuAI",
        "no_api_key": "⚠️ Укажи API-ключ в настройках (.config AzuAI AI_API_KEY)",
        "no_api_url": "⚠️ Укажи API-эндпоинт в настройках (.config AzuAI AI_API_URL)",
        "no_question": "⚠️ Введи вопрос после команды .ask",
        "thinking": "⏳",
        "no_model": "⚠️ Выбери модель через .aicfg",
        "select_model": "**Выбери модель:**\nСтраница {} из {}",
        "model_selected": "✅ {}",
        "loading_models": "⏳ Загружаю список моделей...",
        "no_models": "⚠️ Не удалось загрузить список моделей",
        "chat_on": "✅",
        "chat_off": "⏹",
        "chat_cleared": "🗑",
        "context_not_active": "⚠️ контекст не активирован",
    }

    def __init__(self):
        self._cached_models = []
        self._contexts: dict[int, dict] = {}
        self._last_fetch_error: str = ""
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "AI_API_URL",
                "https://api.openai.com",
                lambda: "URL эндпоинта OpenAI-Compatible API",
            ),
            loader.ConfigValue(
                "AI_API_KEY",
                "",
                lambda: "API-ключ для OpenAI-Compatible API",
            ),
            loader.ConfigValue(
                "AI_MODEL",
                "",
                lambda: "Выбранная модель (сохраняется после выбора через .aicfg)",
            ),
            loader.ConfigValue(
                "FIRECRAWL_API_KEY",
                "",
                lambda: "API-ключ Firecrawl для веб-поиска (не обязателен: без ключа — keyless с лимитами)",
            ),
        )

    async def client_ready(self, client, db):
        self._client_tg = client
        # Load all existing context files into memory
        ctx_dir = _get_context_dir()
        for fname in os.listdir(ctx_dir):
            if fname.endswith(".json"):
                try:
                    chat_id = int(fname[:-5])
                    self._contexts[chat_id] = _load_context(chat_id)
                except Exception:
                    pass

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get_context(self, chat_id: int) -> dict:
        if chat_id not in self._contexts:
            self._contexts[chat_id] = _load_context(chat_id)
        return self._contexts[chat_id]

    def _persist(self, chat_id: int):
        _save_context(chat_id, self._contexts[chat_id])

    def _get_openai(self) -> AsyncOpenAI | None:
        url = self.config["AI_API_URL"]
        key = self.config["AI_API_KEY"]
        if not url or not key:
            return None
        return AsyncOpenAI(api_key=key, base_url=url.rstrip("/") + "/")

    async def _fetch_models(self, force: bool = False) -> list[str]:
        if self._cached_models and not force:
            return self._cached_models
        url = self.config["AI_API_URL"]
        key = self.config["AI_API_KEY"]
        if not url or not key:
            return []
        # Try /models directly (some APIs don't use /v1/ prefix for models list)
        # then fall back to /v1/models
        for base in [url.rstrip("/") + "/models", url.rstrip("/") + "/v1/models"]:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }
            try:
                req = urllib.request.Request(
                    base,
                    headers=headers,
                    method="GET",
                )
                with urllib.request.urlopen(req) as r:
                    raw = r.read().decode()
                data = json.loads(raw)
                if "data" in data:
                    models = sorted(m["id"] for m in data["data"])
                    self._cached_models = models
                    return models
                elif isinstance(data, list):
                    models = sorted(m.get("id", str(m)) for m in data)
                    self._cached_models = models
                    return models
            except Exception:
                continue

        self._last_fetch_error = "Не удалось получить список моделей ни с одного эндпоинта"
        return []

    def _page_buttons(self, models: list[str], page: int) -> tuple[list, int, int]:
        total = (len(models) + MAX_BUTTONS_PER_PAGE - 1) // MAX_BUTTONS_PER_PAGE or 1
        page = max(1, min(page, total))
        start = (page - 1) * MAX_BUTTONS_PER_PAGE
        chunk = models[start: start + MAX_BUTTONS_PER_PAGE]

        buttons = [[{"text": m, "callback": self._cb_select_model, "args": (m,)}] for m in chunk]

        nav = []
        if page > 1:
            nav.append({"text": "◀", "callback": self._cb_page, "args": (page - 1,)})
        nav.append({"text": f"‹ {page}/{total} ›", "callback": self._cb_noop, "args": ()})
        if page < total:
            nav.append({"text": "▶", "callback": self._cb_page, "args": (page + 1,)})
        if nav:
            buttons.append(nav)
        return buttons, page, total

    async def _web_search(self, query: str) -> str:
        try:
            results = await asyncio.to_thread(
                _firecrawl_search, query, self.config["FIRECRAWL_API_KEY"]
            )
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300] or str(e.reason)
            return f"⚠️ Ошибка поиска (HTTP {e.code}): {detail}"
        except Exception as e:
            return f"⚠️ Ошибка поиска: {e}"

        parts = []
        for item in results:
            title = item.get("title") or ""
            url = item.get("url") or ""
            text = item.get("markdown") or item.get("description") or ""
            parts.append(f"**{title}**\n{url}\n{text[:EXCERPT_CHARS]}")
        return "\n\n---\n\n".join(parts) if parts else "Результатов не найдено"

    async def _check_vision(self, client: AsyncOpenAI, model: str) -> bool:
        """Probe whether model accepts image_url content. Result is cached."""
        if model in _vision_cache:
            return _vision_cache[model]
        model_lower = model.lower()
        if any(kw in model_lower for kw in _OBVIOUSLY_TEXT_ONLY):
            _vision_cache[model] = False
            return False
        # Send a minimal image request with a 1x1 transparent PNG
        tiny_png = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        try:
            await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": "1"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{tiny_png}"}},
                    ]}],
                    max_tokens=1,
                ),
                timeout=15,
            )
            _vision_cache[model] = True
        except Exception as e:
            err = str(e).lower()
            _vision_cache[model] = "image" not in err and "vision" not in err and "multimodal" not in err
        return _vision_cache[model]

    async def _get_reply_content(self, message) -> tuple[str | None, bool]:
        """Returns (content, is_photo)"""
        if not message.is_reply:
            return None, False
        reply = await message.get_reply_message()
        if not reply:
            return None, False

        quote_text = getattr(message.reply_to, "quote_text", None)
        if quote_text:
            return quote_text, False

        if reply.message:
            return reply.message, False

        media = reply.media
        if not media:
            return None, False

        if hasattr(media, "photo"):
            data = await reply.download_media(bytes)
            b64 = base64.b64encode(data).decode()
            return b64, True

        if hasattr(media, "document"):
            doc = media.document
            fname = "file"
            for attr in doc.attributes:
                if hasattr(attr, "file_name"):
                    fname = attr.file_name
                    break
            mime = doc.mime_type or ""

            # Images sent as files (not compressed) — treat as photos
            if mime.startswith("image/"):
                data = await reply.download_media(bytes)
                b64 = base64.b64encode(data).decode()
                return b64, True

            data = await reply.download_media(bytes)
            try:
                text = data.decode("utf-8")
                return f"[Файл {fname}]:\n{text}", False
            except Exception:
                b64 = base64.b64encode(data).decode()
                return f"[Файл {fname} base64]:\n{b64}", False

        return None, False

    async def _call_ai(self, question: str, model: str, chat_id: int, vision_b64: str | None = None) -> tuple[str, bool]:
        """Returns (answer, vision_unsupported)"""
        client = self._get_openai()
        if not client:
            return "⚠️ API не настроен", False

        ctx = self._get_context(chat_id)

        # Probe vision support if unknown
        if vision_b64:
            vision_ok = await self._check_vision(client, model)
        else:
            vision_ok = False

        # Build user content
        if vision_b64 and vision_ok:
            user_content = [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{vision_b64}"}},
            ]
        else:
            user_content = question
        vision_skipped = bool(vision_b64 and not vision_ok)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if ctx.get("enabled") and ctx.get("history"):
            messages.extend(ctx["history"])
        messages.append({"role": "user", "content": user_content})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for up-to-date information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=4096,
                ),
                timeout=REQUEST_TIMEOUT,
            )

            msg = response.choices[0].message

            # Handle tool calls. The proxy may hand back calls we never declared
            # (e.g. bash); every call still needs a matching tool message or the
            # follow-up request is rejected. Pass a plain dict too: the SDK's
            # message objects fail to serialize on some OpenAI-compatible APIs.
            if msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    if tc.function.name == "web_search":
                        try:
                            args = json.loads(tc.function.arguments or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        result = await self._web_search(args.get("query", ""))
                    else:
                        result = f"Инструмент {tc.function.name!r} недоступен."
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

                response2 = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=4096,
                    ),
                    timeout=REQUEST_TIMEOUT,
                )
                answer = _message_text(response2.choices[0].message)
                if not answer:
                    # Empty 200 happens when the proxy cuts a reasoning answer
                    # or the model keeps calling tools. Ask once more, plain.
                    messages.append({
                        "role": "user",
                        "content": "Ответь на вопрос выше обычным текстом, без инструментов.",
                    })
                    response3 = await asyncio.wait_for(
                        client.chat.completions.create(
                            model=model,
                            messages=messages,
                            max_tokens=4096,
                        ),
                        timeout=REQUEST_TIMEOUT,
                    )
                    answer = _message_text(response3.choices[0].message)
            else:
                answer = _message_text(msg)

            # Update context
            if ctx.get("enabled"):
                ctx["history"].append({"role": "user", "content": question})
                ctx["history"].append({"role": "assistant", "content": answer})
                # Keep last 20 messages
                if len(ctx["history"]) > 20:
                    ctx["history"] = ctx["history"][-20:]
                self._persist(chat_id)

            return answer, vision_skipped

        except asyncio.TimeoutError:
            return f"⚠️ Время ожидания истекло ({REQUEST_TIMEOUT}с)", False
        except Exception as e:
            return f"⚠️ {e}", False


    def _format_answer(self, question: str, answer: str, model: str, vision_skipped: bool) -> str:
        """Question on top, rich markdown answer below."""
        question = question.strip()
        if len(question) > 1000:
            question = question[:1000] + "…"

        answer = _strip_fences(answer).strip() or "⚠️ Пустой ответ"
        if len(answer) > 30000:
            answer = answer[:30000] + "\n\n*…ответ обрезан*"

        quoted = "\n".join(f"> {line}" if line else ">" for line in question.splitlines())
        parts = []
        if vision_skipped:
            parts.append("**⚠️ фото не отправлено — модель не поддерживает vision**")
        parts.append(quoted)
        parts.append(f"---\n\n**〔{model}〕**\n\n{answer}")
        return "\n\n".join(parts)

    # ── commands ──────────────────────────────────────────────────────────────

    async def askcmd(self, message):
        """.ask [вопрос] — задать вопрос AI. Если без текста — использует реплей как вопрос."""
        args = utils.get_args_raw(message)

        if not self.config["AI_API_URL"]:
            await utils.answer(message, self.strings["no_api_url"])
            return
        if not self.config["AI_API_KEY"]:
            await utils.answer(message, self.strings["no_api_key"])
            return

        model = self.config["AI_MODEL"]
        if not model:
            await utils.answer(message, self.strings["no_model"])
            return
        # Config may store a numeric-named model as int (e.g. "1") — API
        # requires a string, so coerce before use
        model = str(model)

        reply_content, is_photo = await self._get_reply_content(message)
        vision_b64 = None

        if reply_content:
            if is_photo:
                vision_b64 = reply_content
                # If no text args, use a default prompt for the photo
                if not args:
                    args = "Опиши это изображение"
            else:
                if args:
                    args = f"{args}\n\n{reply_content}"
                else:
                    args = reply_content

        if not args:
            await utils.answer(message, self.strings["no_question"])
            return

        chat_id = utils.get_chat_id(message)

        answer, vision_skipped = await self._call_ai(args, model, chat_id, vision_b64)
        body = self._format_answer(args, answer, model, vision_skipped)

        # Same delivery as Pinger: for own outgoing messages utils.answer edits
        # the command in place, and the framework turns the text into a native
        # rich message (premium account). Works in PMs, no inline bot needed.
        await utils.answer(message, body)

    async def chatcmd(self, message):
        """.chat — включить/выключить режим контекста"""
        chat_id = utils.get_chat_id(message)
        ctx = self._get_context(chat_id)
        ctx["enabled"] = not ctx.get("enabled", False)
        self._persist(chat_id)
        await utils.answer(message, self.strings["chat_on"] if ctx["enabled"] else self.strings["chat_off"])

    async def clearchatcmd(self, message):
        """.clearchat — очистить контекст текущего чата"""
        chat_id = utils.get_chat_id(message)
        ctx = self._get_context(chat_id)
        if not ctx.get("enabled"):
            await utils.answer(message, self.strings["context_not_active"])
            return
        ctx["history"] = []
        _delete_context(chat_id)
        self._contexts.pop(chat_id, None)
        await utils.answer(message, self.strings["chat_cleared"])

    async def aicfgcmd(self, message):
        """.aicfg [refresh] — выбор модели. С аргументом refresh обновит кэш."""
        args = utils.get_args_raw(message)
        if args and args.strip().lower() == "refresh":
            self._cached_models = []
        await utils.answer(message, self.strings["loading_models"])
        models = await self._fetch_models(force=(args and args.strip().lower() == "refresh"))
        if not models:
            err = self._last_fetch_error or "неизвестная ошибка"
            await utils.answer(message, f"{self.strings['no_models']}\n\n<code>{err}</code>")
            return

        buttons, page, total = self._page_buttons(models, 1)
        text = self.strings["select_model"].format(page, total)
        await self.inline.form(text=text, reply_markup=buttons, message=message)

    async def _cb_noop(self, call: InlineCall):
        await call.answer()

    async def _cb_page(self, call: InlineCall, page: int):
        models = await self._fetch_models()
        if not models:
            return
        buttons, page, total = self._page_buttons(models, page)
        await call.edit(
            text=self.strings["select_model"].format(page, total),
            reply_markup=buttons,
        )

    async def _cb_select_model(self, call: InlineCall, model: str):
        # ast.literal_eval in ConfigValue turns "1" into int 1, which the API
        # rejects with 400 "model: expected string, received number" — coerce
        self.config["AI_MODEL"] = str(model)
        await call.edit(self.strings["model_selected"].format(model))
        await call.answer(f"Модель: {model}")
