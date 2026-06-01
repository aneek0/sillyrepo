# meta developer: Azu-nyyyyyyaaaaan

"""
Генератор голосовых с waveform в форме фигур.

Waveform в Telegram — массив значений 0-31, которые отрисовываются
как вертикальные полоски. Задавая нужные значения, можно получить
фигуру: сердечко, волну, зигзаг и т.д.

Команды:
  .vheart [текст] — waveform-сердечко
  .vwave [текст] — waveform-синусоида
  .vzigzag [текст] — waveform-зигзаг
  .vtriangle [текст] — waveform-треугольник
  .vrect [текст] — waveform-прямоугольник
  .vtext <текст> — waveform из букв (каждая буква = уровень)
  .vshape <паттерн> — waveform из ASCII-символов высоты

Если текст не указан — отправляется тишина с waveform.
Если текст указан — TTS с этим waveform.
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

SAMPLE_RATE = 48000
CHANNELS = 1
WAVEFORM_POINTS = 64  # количество точек в waveform (Telegram сам интерполирует)

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


# ── генерация waveform-фигур ──────────────────────────────────────────────

def _wf_heart(points: int = WAVEFORM_POINTS) -> list[int]:
    """Сердечко ♡"""
    vals = []
    for i in range(points):
        t = i / points * 2 * math.pi
        # Параметрическое сердце
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
        # Нормализуем к 0-31
        val = int(15.5 + 14 * y / 30)
        vals.append(max(0, min(31, val)))
    return vals


def _wf_sine(points: int = WAVEFORM_POINTS) -> list[int]:
    """Синусоида ∿"""
    vals = []
    for i in range(points):
        t = i / points * 2 * math.pi
        val = int(15.5 + 14 * math.sin(t))
        vals.append(max(0, min(31, val)))
    return vals


def _wf_zigzag(points: int = WAVEFORM_POINTS) -> list[int]:
    """Зигзаг ⚡"""
    vals = []
    period = 8
    for i in range(points):
        pos = i % period
        if pos < period // 2:
            val = int(pos * 31 / (period // 2))
        else:
            val = int((period - pos) * 31 / (period // 2))
        vals.append(max(0, min(31, val)))
    return vals


def _wf_triangle(points: int = WAVEFORM_POINTS) -> list[int]:
    """Треугольник △"""
    vals = []
    for i in range(points):
        t = i / points
        if t < 0.5:
            val = int(t * 2 * 31)
        else:
            val = int((1 - t) * 2 * 31)
        vals.append(max(0, min(31, val)))
    return vals


def _wf_rect(points: int = WAVEFORM_POINTS) -> list[int]:
    """Прямоугольник ▭"""
    vals = []
    for i in range(points):
        if 0.2 < i / points < 0.8:
            vals.append(31)
        else:
            vals.append(2)
    return vals


def _wf_from_text(text: str, points: int = WAVEFORM_POINTS) -> list[int]:
    """Waveform из текста — каждый символ даёт уровень."""
    if not text:
        return [16] * points
    vals = []
    for i in range(points):
        ch_idx = i * len(text) // points
        ch = text[ch_idx]
        val = ord(ch) % 32
        vals.append(val)
    return vals


def _wf_from_ascii(pattern: str, points: int = WAVEFORM_POINTS) -> list[int]:
    """Waveform из ASCII-символов высоты (▁▂▃▄▅▆▇█ .:-=+*#%@)."""
    levels = " .:-=+*#%@▁▂▃▄▅▆▇█"
    if not pattern:
        return [16] * points
    raw = []
    for ch in pattern:
        idx = levels.find(ch)
        if idx < 0:
            raw.append(15)
        else:
            raw.append(int(idx * 31 / (len(levels) - 1)))
    # Интерполируем до points
    if len(raw) < points:
        vals = []
        for i in range(points):
            src = i * len(raw) // points
            vals.append(raw[src])
        return vals
    return raw[:points]


# ── генерация аудио ───────────────────────────────────────────────────────

def _gen_silence(duration_ms: float) -> bytes:
    n = int(SAMPLE_RATE * duration_ms / 1000)
    return b"\x00\x00" * n


def _gen_sine(freq: float, duration_ms: float, amp: float = 0.5) -> bytes:
    n = int(SAMPLE_RATE * duration_ms / 1000)
    frames = []
    for i in range(n):
        t = i / SAMPLE_RATE
        s = amp * 32767 * math.sin(2 * math.pi * freq * t)
        frames.append(struct.pack("<h", max(-32768, min(32767, int(s)))))
    return b"".join(frames)


def _pcm_to_ogg(pcm: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as f:
        f.write(pcm)
        fin = f.name
    out = fin + ".ogg"
    try:
        subprocess.run(
            ["ffmpeg", "-y",
             "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS),
             "-i", fin,
             "-c:a", "libopus", "-b:a", "64k", "-vbr", "on",
             out],
            capture_output=True, timeout=30)
        with open(out, "rb") as f:
            return f.read()
    finally:
        os.unlink(fin)
        if os.path.exists(out):
            os.unlink(out)


async def _tts_to_ogg(text: str, voice: str) -> bytes:
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError("edge-tts не установлен: pip install edge-tts")
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
            capture_output=True, timeout=30)
        with open(out, "rb") as f:
            return f.read()
    finally:
        os.unlink(fin)
        if os.path.exists(out):
            os.unlink(out)


def _get_duration_ms(ogg: bytes) -> int:
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(ogg)
        path = f.name
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10)
        return int(float(r.stdout.strip()) * 1000)
    except Exception:
        return 3000
    finally:
        os.unlink(path)


# ── модуль ─────────────────────────────────────────────────────────────────

@loader.tds
class VoiceWaveMod(loader.Module):
    """Голосовые с waveform-фигурами"""

    strings = {
        "name": "VoiceWave",
        "no_text": "⚠️ Введи текст",
        "no_pattern": "⚠️ Введи ASCII-паттерн",
        "generating": "⏳",
        "error": "⚠️ {}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("TTS_VOICE", "ru-RU-SvetlanaNeural", lambda: "Голос edge-tts"),
        )

    async def _send(self, message, ogg: bytes, waveform_vals: list[int], dur_ms: int = 0):
        if dur_ms <= 0:
            dur_ms = _get_duration_ms(ogg)
        if dur_ms <= 0:
            dur_ms = 3000

        enc_wf = encode_waveform(waveform_vals)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(ogg)
            path = f.name
        try:
            attr = DocumentAttributeAudio(
                duration=dur_ms // 1000,
                voice=True,
                waveform=enc_wf,
            )
            await self._client.send_file(
                message.peer_id, path,
                attributes=[attr],
                reply_to=message.reply_to_msg_id if message.is_reply else None,
            )
            await message.delete()
        finally:
            os.unlink(path)

    async def _get_audio(self, message, text: str | None) -> tuple[bytes, int]:
        """Возвращает (ogg_bytes, duration_ms). Если text=None — тишина."""
        if text:
            voice = self.config["TTS_VOICE"]
            ogg = await asyncio.wait_for(_tts_to_ogg(text, voice), timeout=30)
            dur = _get_duration_ms(ogg)
            return ogg, dur
        else:
            dur = 3000
            pcm = _gen_silence(dur)
            ogg = await asyncio.get_event_loop().run_in_executor(None, _pcm_to_ogg, pcm)
            return ogg, dur

    # ── фигуры ─────────────────────────────────────────────────────────

    async def vheartcmd(self, message):
        """.vheart [текст] — голосовое с waveform-сердечком ♡"""
        text = utils.get_args_raw(message) or None
        await utils.answer(message, self.strings["generating"])
        try:
            ogg, dur = await self._get_audio(message, text)
            wf = _wf_heart()
            await self._send(message, ogg, wf, dur)
        except Exception as e:
            logger.exception("vheart")
            await utils.answer(message, self.strings["error"].format(e))

    async def vsinecmd(self, message):
        """.vsine [текст] — голосовое с waveform-синусоидой ∿"""
        text = utils.get_args_raw(message) or None
        await utils.answer(message, self.strings["generating"])
        try:
            ogg, dur = await self._get_audio(message, text)
            wf = _wf_sine()
            await self._send(message, ogg, wf, dur)
        except Exception as e:
            logger.exception("vsine")
            await utils.answer(message, self.strings["error"].format(e))

    async def vzigzagcmd(self, message):
        """.vzigzag [текст] — голосовое с waveform-зигзагом ⚡"""
        text = utils.get_args_raw(message) or None
        await utils.answer(message, self.strings["generating"])
        try:
            ogg, dur = await self._get_audio(message, text)
            wf = _wf_zigzag()
            await self._send(message, ogg, wf, dur)
        except Exception as e:
            logger.exception("vzigzag")
            await utils.answer(message, self.strings["error"].format(e))

    async def vtrianglecmd(self, message):
        """.vtriangle [текст] — голосовое с waveform-треугольником △"""
        text = utils.get_args_raw(message) or None
        await utils.answer(message, self.strings["generating"])
        try:
            ogg, dur = await self._get_audio(message, text)
            wf = _wf_triangle()
            await self._send(message, ogg, wf, dur)
        except Exception as e:
            logger.exception("vtriangle")
            await utils.answer(message, self.strings["error"].format(e))

    async def vrectcmd(self, message):
        """.vrect [текст] — голосовое с waveform-прямоугольником ▭"""
        text = utils.get_args_raw(message) or None
        await utils.answer(message, self.strings["generating"])
        try:
            ogg, dur = await self._get_audio(message, text)
            wf = _wf_rect()
            await self._send(message, ogg, wf, dur)
        except Exception as e:
            logger.exception("vrect")
            await utils.answer(message, self.strings["error"].format(e))

    async def vtextcmd(self, message):
        """.vtext <текст> — waveform из букв текста"""
        text = utils.get_args_raw(message)
        if not text:
            await utils.answer(message, self.strings["no_text"])
            return
        await utils.answer(message, self.strings["generating"])
        try:
            ogg, dur = await self._get_audio(message, text)
            wf = _wf_from_text(text)
            await self._send(message, ogg, wf, dur)
        except Exception as e:
            logger.exception("vtext")
            await utils.answer(message, self.strings["error"].format(e))

    async def vshapecmd(self, message):
        """.vshape <паттерн> [текст] — waveform из ASCII-символов высоты.
        Символы: ▁▂▃▄▅▆▇█ или .:-=+*#%@
        Пример: .vshape ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁ Привет мир"""
        args = utils.get_args(message)
        if not args:
            await utils.answer(message, self.strings["no_pattern"])
            return

        pattern = args[0]
        text = " ".join(args[1:]) if len(args) > 1 else None

        await utils.answer(message, self.strings["generating"])
        try:
            ogg, dur = await self._get_audio(message, text)
            wf = _wf_from_ascii(pattern)
            await self._send(message, ogg, wf, dur)
        except Exception as e:
            logger.exception("vshape")
            await utils.answer(message, self.strings["error"].format(e))
