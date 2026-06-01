# meta developer: Azu-nyyyyyyaaaaan

"""
Генератор голосовых сообщений с особыми формами волны.

Режимы:
  .vwave <текст> — TTS голосовое (edge-tts)
  .vshape <паттерн> — генерация аудио по ASCII-паттерну амплитуды
  .vbeep <freq> <dur_ms> — простой синусоидальный тон
  .vsweep <start_freq> <end_freq> <dur_ms> — свип (чирп)

Паттерн для .vshape: строка из символов ▁▂▃▄▅▆▇█ или .:-=+*#%@
Каждый символ = один фрейм амплитуды (50мс). Чем выше символ — тем громче.
"""

import asyncio
import io
import math
import os
import struct
import subprocess
import tempfile

import logging

from .. import loader, utils

logger = logging.getLogger(__name__)

# ── конфигурация ──────────────────────────────────────────────────────────

SAMPLE_RATE = 48000       # Telegram требует 48kHz для Opus
CHANNELS = 1              # моно
SAMPLE_WIDTH = 2          # 16-bit PCM
FRAME_MS = 50             # длительность одного фрейма паттерна (мс)
SWEEP_STEP_MS = 20        # шаг генерации свипа (мс)

# ── ASCII → амплитуда ────────────────────────────────────────────────────

_ASCII_LEVELS = " .:-=+*#%@▁▂▃▄▅▆▇█"


def _char_to_level(ch: str) -> float:
    """Символ → уровень амплитуды 0.0 … 1.0"""
    idx = _ASCII_LEVELS.find(ch)
    if idx < 0:
        return 0.5   # неизвестный символ = средняя громкость
    return idx / (len(_ASCII_LEVELS) - 1)


# ── генерация PCM ─────────────────────────────────────────────────────────

def _gen_sine(freq: float, duration_ms: float, amplitude: float = 0.8) -> bytes:
    """Синусоида, возвращает PCM 16-bit LE."""
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    frames = []
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        sample = amplitude * 32767 * math.sin(2 * math.pi * freq * t)
        sample = max(-32768, min(32767, int(sample)))
        frames.append(struct.pack("<h", sample))
    return b"".join(frames)


def _gen_silence(duration_ms: float) -> bytes:
    """Тишина."""
    n_samples = int(SAMPLE_RATE * duration_ms / 1000)
    return b"\x00\x00" * n_samples


def _gen_shape(pattern: str, base_freq: float = 440.0) -> bytes:
    """
    Генерирует аудио по ASCII-паттерну.
    Каждый символ = FRAME_MS миллисекунд синусоиды с амплитудой по символу.
    Пустые символы (пробел, точка) = тишина/тихий тон.
    """
    parts = []
    for ch in pattern:
        level = _char_to_level(ch)
        if level < 0.05:
            parts.append(_gen_silence(FRAME_MS))
        else:
            parts.append(_gen_sine(base_freq, FRAME_MS, amplitude=level))
    return b"".join(parts)


def _gen_sweep(start_freq: float, end_freq: float, duration_ms: float) -> bytes:
    """Линейный свип частоты."""
    total_samples = int(SAMPLE_RATE * duration_ms / 1000)
    step_samples = int(SAMPLE_RATE * SWEEP_STEP_MS / 1000)
    frames = []
    for i in range(0, total_samples, step_samples):
        frac = i / total_samples if total_samples > 0 else 0
        freq = start_freq + (end_freq - start_freq) * frac
        chunk = _gen_sine(freq, SWEEP_STEP_MS, amplitude=0.8)
        frames.append(chunk)
    return b"".join(frames)


# ── WAV → OGG/Opus ────────────────────────────────────────────────────────

def _pcm_to_ogg(pcm_bytes: bytes) -> bytes:
    """Конвертирует PCM 16-bit LE mono 48kHz в OGG/Opus через ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as fin:
        fin.write(pcm_bytes)
        fin_name = fin.name

    out_name = fin_name + ".ogg"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "s16le",
                "-ar", str(SAMPLE_RATE),
                "-ac", str(CHANNELS),
                "-i", fin_name,
                "-c:a", "libopus",
                "-b:a", "64k",
                "-vbr", "on",
                out_name,
            ],
            capture_output=True,
            timeout=30,
        )
        with open(out_name, "rb") as f:
            return f.read()
    finally:
        os.unlink(fin_name)
        if os.path.exists(out_name):
            os.unlink(out_name)


# ── TTS ────────────────────────────────────────────────────────────────────

async def _tts_to_ogg(text: str, voice: str) -> bytes:
    """Edge TTS → OGG/Opus."""
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError("edge-tts не установлен: pip install edge-tts")
    communicate = edge_tts.Communicate(text, voice=voice)
    mp3_buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_buf.write(chunk["data"])
    mp3_buf.seek(0)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fin:
        fin.write(mp3_buf.read())
        fin_name = fin.name

    out_name = fin_name + ".ogg"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", fin_name,
                "-c:a", "libopus",
                "-b:a", "64k",
                "-vbr", "on",
                "-ar", "48000",
                "-ac", "1",
                out_name,
            ],
            capture_output=True,
            timeout=30,
        )
        with open(out_name, "rb") as f:
            return f.read()
    finally:
        os.unlink(fin_name)
        if os.path.exists(out_name):
            os.unlink(out_name)


# ── модуль ─────────────────────────────────────────────────────────────────

@loader.tds
class VoiceWaveMod(loader.Module):
    """Генератор голосовых с особыми формами волны"""

    strings = {
        "name": "VoiceWave",
        "no_text": "⚠️ Введи текст",
        "no_pattern": "⚠️ Введи паттерн (например ▁▂▃▄▅▆▇█)",
        "no_args": "⚠️ Укажи аргументы",
        "generating": "⏳ Генерирую…",
        "error": "⚠️ Ошибка: {}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "TTS_VOICE",
                "ru-RU-SvetlanaNeural",
                lambda: "Голос edge-tts (например ru-RU-SvetlanaNeural)",
            ),
            loader.ConfigValue(
                "SHAPE_FREQ",
                440,
                lambda: "Базовая частота для .vshape (Гц)",
            ),
        )

    # ── .vwave — TTS голосовое ──────────────────────────────────────────

    async def vwavecmd(self, message):
        """.vwave <текст> — сгенерировать голосовое из текста"""
        text = utils.get_args_raw(message)
        if not text:
            await utils.answer(message, self.strings["no_text"])
            return

        await utils.answer(message, self.strings["generating"])
        try:
            voice = self.config["TTS_VOICE"]
            ogg = await asyncio.wait_for(
                _tts_to_ogg(text, voice),
                timeout=30,
            )
            await self._send_voice(message, ogg)
        except asyncio.TimeoutError:
            await utils.answer(message, self.strings["error"].format("таймаут TTS"))
        except Exception as e:
            logger.exception("vwave error")
            await utils.answer(message, self.strings["error"].format(e))

    # ── .vshape — форма волны из ASCII ──────────────────────────────────

    async def vshapecmd(self, message):
        """.vshape <паттерн> — аудио по ASCII-паттерну (▁▂▃▄▅▆▇█ или .:-=+*#%@)"""
        pattern = utils.get_args_raw(message)
        if not pattern:
            await utils.answer(message, self.strings["no_pattern"])
            return

        # Лимит: 200 символов = ~10 секунд
        if len(pattern) > 200:
            pattern = pattern[:200]

        await utils.answer(message, self.strings["generating"])

        def _generate():
            freq = int(self.config["SHAPE_FREQ"])
            pcm = _gen_shape(pattern, base_freq=freq)
            return _pcm_to_ogg(pcm)

        try:
            ogg = await asyncio.get_event_loop().run_in_executor(None, _generate)
            await self._send_voice(message, ogg)
        except Exception as e:
            logger.exception("vshape error")
            await utils.answer(message, self.strings["error"].format(e))

    # ── .vbeep — синусоидальный тон ─────────────────────────────────────

    async def vbeepcmd(self, message):
        """.vbeep <частота_Гц> <длительность_мс> — синусоидальный тон"""
        args = utils.get_args(message)
        if len(args) < 2:
            await utils.answer(message, self.strings["no_args"])
            return

        try:
            freq = float(args[0])
            dur = float(args[1])
        except ValueError:
            await utils.answer(message, self.strings["error"].format("неверные числа"))
            return

        await utils.answer(message, self.strings["generating"])

        def _generate():
            pcm = _gen_sine(freq, dur, amplitude=0.8)
            return _pcm_to_ogg(pcm)

        try:
            ogg = await asyncio.get_event_loop().run_in_executor(None, _generate)
            await self._send_voice(message, ogg)
        except Exception as e:
            logger.exception("vbeep error")
            await utils.answer(message, self.strings["error"].format(e))

    # ── .vsweep — свип ──────────────────────────────────────────────────

    async def vsweepcmd(self, message):
        """.vsweep <start_freq> <end_freq> <dur_ms> — свип (чирп)"""
        args = utils.get_args(message)
        if len(args) < 3:
            await utils.answer(message, self.strings["no_args"])
            return

        try:
            f_start = float(args[0])
            f_end = float(args[1])
            dur = float(args[2])
        except ValueError:
            await utils.answer(message, self.strings["error"].format("неверные числа"))
            return

        await utils.answer(message, self.strings["generating"])

        def _generate():
            pcm = _gen_sweep(f_start, f_end, dur)
            return _pcm_to_ogg(pcm)

        try:
            ogg = await asyncio.get_event_loop().run_in_executor(None, _generate)
            await self._send_voice(message, ogg)
        except Exception as e:
            logger.exception("vsweep error")
            await utils.answer(message, self.strings["error"].format(e))

    # ── вспомогательное ──────────────────────────────────────────────────

    async def _send_voice(self, message, ogg_bytes: bytes):
        """Отправить ogg/opus как голосовое сообщение."""
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(ogg_bytes)
            path = f.name
        try:
            await self._client.send_file(
                message.peer_id,
                path,
                voice_note=True,
                reply_to=message.reply_to_msg_id if message.is_reply else None,
            )
            await message.delete()
        finally:
            os.unlink(path)
