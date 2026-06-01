# meta developer: Azu-nyyyyyyaaaaan

"""
Генератор голосовых сообщений с кастомным waveform (формой волны).

Telegram отображает в голосовых visualization — полоски громкости.
Обычно они вычисляются из аудио, но можно задать явно через waveform.

Команды:
  .vwave <текст> — TTS голосовое с waveform из текста
  .vshape <паттерн> — waveform из ASCII-паттерна (▁▂▃▄▅▆▇█ или .:-=+*#%@)
  .vbeep <freq> <dur_ms> — синусоидальный тон с круглым waveform
  .vsweep <start> <end> <dur_ms> — свип с линейным waveform
  .vcustom <паттерн> — произвольный waveform на любом аудио

Waveform кодируется как 5-bit значения (0-31), упакованные в байты.
"""

import asyncio
import io
import logging
import math
import os
import struct
import subprocess
import tempfile

from telethon.tl.types import DocumentAttributeAudio

from .. import loader, utils

logger = logging.getLogger(__name__)

# ── конфигурация ──────────────────────────────────────────────────────────

SAMPLE_RATE = 48000
CHANNELS = 1
SAMPLE_WIDTH = 2
FRAME_MS = 50
SWEEP_STEP_MS = 20
MAX_PATTERN_LEN = 200

# ── ASCII → уровень ──────────────────────────────────────────────────────

_ASCII_LEVELS = " .:-=+*#%@▁▂▃▄▅▆▇█"


def _char_to_level(ch: str) -> int:
    """Символ → уровень 0-31"""
    idx = _ASCII_LEVELS.find(ch)
    if idx < 0:
        return 15
    return int(idx * 31 / (len(_ASCII_LEVELS) - 1))


# ── waveform encoding ─────────────────────────────────────────────────────

def encode_waveform(values: list[int]) -> bytes:
    """Упаковка значений 0-31 в 5-битный формат Telegram."""
    result = bytearray()
    buffer = 0
    bits = 0
    for val in values:
        val = max(0, min(31, val))
        buffer = (buffer << 5) | val
        bits += 5
        while bits >= 8:
            bits -= 8
            result.append((buffer >> bits) & 0xFF)
    if bits > 0:
        result.append((buffer << (8 - bits)) & 0xFF)
    return bytes(result)


def decode_waveform(data: bytes) -> list[int]:
    """Распаковка 5-битного waveform."""
    values = []
    buffer = 0
    bits = 0
    for byte in data:
        buffer = (buffer << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            values.append((buffer >> bits) & 0x1F)
    return values


# ── генерация waveform-паттернов ──────────────────────────────────────────

def _waveform_from_text(text: str, target_len: int = 50) -> list[int]:
    """Генерирует waveform из текста (по кодам символов)."""
    if not text:
        return [16] * target_len
    step = max(1, len(text) // target_len)
    vals = []
    for i in range(0, len(text), step):
        ch = text[i]
        # Код символа → уровень 0-31
        val = (ord(ch) % 32)
        vals.append(val)
    # Интерполируем до target_len
    if len(vals) < target_len:
        result = []
        for i in range(target_len):
            src_idx = i * len(vals) // target_len
            result.append(vals[src_idx])
        return result
    return vals[:target_len]


def _waveform_from_pattern(pattern: str) -> list[int]:
    """Waveform из ASCII-паттерна."""
    if not pattern:
        return [16]
    return [_char_to_level(ch) for ch in pattern]


def _waveform_circle(radius: int = 16, points: int = 64) -> list[int]:
    """Круг/овал waveform."""
    vals = []
    for i in range(points):
        angle = 2 * math.pi * i / points
        val = int(15.5 + radius * math.sin(angle))
        vals.append(max(0, min(31, val)))
    return vals


def _waveform_linear(start: int, end: int, points: int = 50) -> list[int]:
    """Линейный waveform от start до end."""
    vals = []
    for i in range(points):
        frac = i / max(1, points - 1)
        val = int(start + (end - start) * frac)
        vals.append(max(0, min(31, val)))
    return vals


# ── генерация PCM ─────────────────────────────────────────────────────────

def _gen_sine(freq: float, duration_ms: float, amplitude: float = 0.8) -> bytes:
    n = int(SAMPLE_RATE * duration_ms / 1000)
    frames = []
    for i in range(n):
        t = i / SAMPLE_RATE
        s = amplitude * 32767 * math.sin(2 * math.pi * freq * t)
        frames.append(struct.pack("<h", max(-32768, min(32767, int(s)))))
    return b"".join(frames)


def _gen_silence(duration_ms: float) -> bytes:
    n = int(SAMPLE_RATE * duration_ms / 1000)
    return b"\x00\x00" * n


def _gen_sweep(start_freq: float, end_freq: float, duration_ms: float) -> bytes:
    step = SWEEP_STEP_MS
    parts = []
    t = 0.0
    while t < duration_ms:
        frac = t / duration_ms if duration_ms > 0 else 0
        freq = start_freq + (end_freq - start_freq) * frac
        dur = min(step, duration_ms - t)
        parts.append(_gen_sine(freq, dur))
        t += step
    return b"".join(parts)


# ── WAV → OGG/Opus ────────────────────────────────────────────────────────

def _pcm_to_ogg(pcm_bytes: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as f:
        f.write(pcm_bytes)
        fin = f.name
    out = fin + ".ogg"
    try:
        subprocess.run(
            ["ffmpeg", "-y",
             "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
             "-i", fin,
             "-c:a", "libopus", "-b:a", "64k", "-vbr", "on",
             out],
            capture_output=True, timeout=30,
        )
        with open(out, "rb") as f:
            return f.read()
    finally:
        os.unlink(fin)
        if os.path.exists(out):
            os.unlink(out)


# ── TTS ────────────────────────────────────────────────────────────────────

async def _tts_to_ogg(text: str, voice: str) -> bytes:
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError("edge-tts не установлен")
    comm = edge_tts.Communicate(text, voice=voice)
    buf = io.BytesIO()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(buf.read())
        fin = f.name
    out = fin + ".ogg"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", fin,
             "-c:a", "libopus", "-b:a", "64k", "-vbr", "on",
             "-ar", "48000", "-ac", "1", out],
            capture_output=True, timeout=30,
        )
        with open(out, "rb") as f:
            return f.read()
    finally:
        os.unlink(fin)
        if os.path.exists(out):
            os.unlink(out)


def _get_duration_ms(ogg_bytes: bytes) -> int:
    """Определяет длительность ogg/opus через ffprobe."""
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(ogg_bytes)
        path = f.name
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10,
        )
        return int(float(r.stdout.strip()) * 1000)
    except Exception:
        return 0
    finally:
        os.unlink(path)


# ── модуль ─────────────────────────────────────────────────────────────────

@loader.tds
class VoiceWaveMod(loader.Module):
    """Генератор голосовых с кастомным waveform"""

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
                "TTS_VOICE", "ru-RU-SvetlanaNeural",
                lambda: "Голос edge-tts",
            ),
            loader.ConfigValue(
                "SHAPE_FREQ", 440,
                lambda: "Базовая частота для .vshape (Гц)",
            ),
        )

    async def _send_voice(self, message, ogg_bytes: bytes, waveform: bytes, duration_ms: int = 0):
        """Отправить ogg/opus как голосовое с кастомным waveform."""
        if duration_ms <= 0:
            duration_ms = _get_duration_ms(ogg_bytes)
        if duration_ms <= 0:
            duration_ms = 3000  # fallback

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(ogg_bytes)
            path = f.name
        try:
            attr = DocumentAttributeAudio(
                duration=duration_ms // 1000,
                voice=True,
                waveform=waveform,
            )
            await self._client.send_file(
                message.peer_id,
                path,
                attributes=[attr],
                reply_to=message.reply_to_msg_id if message.is_reply else None,
            )
            await message.delete()
        finally:
            os.unlink(path)

    # ── .vwave — TTS с waveform из текста ──────────────────────────────

    async def vwavecmd(self, message):
        """.vwave <текст> — TTS голосовое, waveform генерируется из текста"""
        text = utils.get_args_raw(message)
        if not text:
            await utils.answer(message, self.strings["no_text"])
            return

        await utils.answer(message, self.strings["generating"])
        try:
            voice = self.config["TTS_VOICE"]
            ogg = await asyncio.wait_for(_tts_to_ogg(text, voice), timeout=30)
            wf = _waveform_from_text(text)
            enc_wf = encode_waveform(wf)
            dur = _get_duration_ms(ogg)
            await self._send_voice(message, ogg, enc_wf, dur)
        except asyncio.TimeoutError:
            await utils.answer(message, self.strings["error"].format("таймаут"))
        except Exception as e:
            logger.exception("vwave error")
            await utils.answer(message, self.strings["error"].format(e))

    # ── .vshape — waveform из ASCII-паттерна ────────────────────────────

    async def vshapecmd(self, message):
        """.vshape <паттерн> — waveform из ASCII (▁▂▃▄▅▆▇█ или .:-=+*#%@)"""
        pattern = utils.get_args_raw(message)
        if not pattern:
            await utils.answer(message, self.strings["no_pattern"])
            return
        if len(pattern) > MAX_PATTERN_LEN:
            pattern = pattern[:MAX_PATTERN_LEN]

        await utils.answer(message, self.strings["generating"])
        try:
            freq = int(self.config["SHAPE_FREQ"])
            pcm = _gen_sine(freq, len(pattern) * FRAME_MS)
            ogg = await asyncio.get_event_loop().run_in_executor(None, _pcm_to_ogg, pcm)
            wf = _waveform_from_pattern(pattern)
            enc_wf = encode_waveform(wf)
            dur = len(pattern) * FRAME_MS
            await self._send_voice(message, ogg, enc_wf, dur)
        except Exception as e:
            logger.exception("vshape error")
            await utils.answer(message, self.strings["error"].format(e))

    # ── .vbeep — тон с круглым waveform ─────────────────────────────────

    async def vbeepcmd(self, message):
        """.vbeep <частота_Гц> <длительность_мс> — синусоида с круглым waveform"""
        args = utils.get_args(message)
        if len(args) < 2:
            await utils.answer(message, self.strings["no_args"])
            return
        try:
            freq, dur = float(args[0]), float(args[1])
        except ValueError:
            await utils.answer(message, self.strings["error"].format("неверные числа"))
            return

        await utils.answer(message, self.strings["generating"])
        try:
            pcm = _gen_sine(freq, dur)
            ogg = await asyncio.get_event_loop().run_in_executor(None, _pcm_to_ogg, pcm)
            wf = _waveform_circle(15, 64)
            enc_wf = encode_waveform(wf)
            await self._send_voice(message, ogg, enc_wf, int(dur))
        except Exception as e:
            logger.exception("vbeep error")
            await utils.answer(message, self.strings["error"].format(e))

    # ── .vsweep — свип с линейным waveform ──────────────────────────────

    async def vsweepcmd(self, message):
        """.vsweep <start_freq> <end_freq> <dur_ms> — свип с линейным waveform"""
        args = utils.get_args(message)
        if len(args) < 3:
            await utils.answer(message, self.strings["no_args"])
            return
        try:
            f0, f1, dur = float(args[0]), float(args[1]), float(args[2])
        except ValueError:
            await utils.answer(message, self.strings["error"].format("неверные числа"))
            return

        await utils.answer(message, self.strings["generating"])
        try:
            pcm = _gen_sweep(f0, f1, dur)
            ogg = await asyncio.get_event_loop().run_in_executor(None, _pcm_to_ogg, pcm)
            wf = _waveform_linear(0, 31, 50)
            enc_wf = encode_waveform(wf)
            await self._send_voice(message, ogg, enc_wf, int(dur))
        except Exception as e:
            logger.exception("vsweep error")
            await utils.answer(message, self.strings["error"].format(e))

    # ── .vcustom — кастомный waveform на TTS аудио ─────────────────────

    async def vcustomcmd(self, message):
        """.vcustom <паттерн> — TTS с waveform из паттерна"""
        args = utils.get_args(message)
        if len(args) < 2:
            await utils.answer(message, self.strings["no_args"])
            return

        # Последний аргумент = паттерн, остальное = текст
        text = " ".join(args[:-1])
        pattern = args[-1]

        if not text:
            await utils.answer(message, self.strings["no_text"])
            return
        if not pattern:
            await utils.answer(message, self.strings["no_pattern"])
            return

        await utils.answer(message, self.strings["generating"])
        try:
            voice = self.config["TTS_VOICE"]
            ogg = await asyncio.wait_for(_tts_to_ogg(text, voice), timeout=30)
            wf = _waveform_from_pattern(pattern)
            enc_wf = encode_waveform(wf)
            dur = _get_duration_ms(ogg)
            await self._send_voice(message, ogg, enc_wf, dur)
        except asyncio.TimeoutError:
            await utils.answer(message, self.strings["error"].format("таймаут"))
        except Exception as e:
            logger.exception("vcustom error")
            await utils.answer(message, self.strings["error"].format(e))
