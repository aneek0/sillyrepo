# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import mimetypes
import os
import re
import requests
from .. import loader, utils


def fmt_time(s):
    """Format seconds to m:ss."""
    if s is None:
        return ""
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


def format_anime_card(res):
    """Build formatted message from trace.moe + anilistInfo response."""
    anilist = res.get("anilist") or {}
    filename = res.get("filename", "")
    name = filename.split(".")[0] if filename else "Неизвестно"
    similarity = res.get("similarity", 0)
    episode = res.get("episode")
    from_time = res.get("from")
    to_time = res.get("to")

    lines = []

    # Titles
    title = anilist.get("title", {})
    english = title.get("english")
    romaji = title.get("romaji")
    native = title.get("native")

    if english:
        lines.append(f"ℹ️ <b>{english}</b>")
        if romaji and romaji != english:
            lines.append(f"   <code>{romaji}</code>")
    elif romaji:
        lines.append(f"ℹ️ <b>{romaji}</b>")

    if native:
        lines.append(f"   <code>{native}</code>")

    # Aliases
    synonyms = anilist.get("synonyms", [])
    if synonyms:
        shown = synonyms[:4]
        lines.append(f"📎 <b>Alias:</b> {', '.join(shown)}")

    # Format + episodes + duration + season
    fmt = anilist.get("format")
    eps = anilist.get("episodes")
    dur = anilist.get("duration")
    season = anilist.get("season")
    season_year = anilist.get("seasonYear")
    status = anilist.get("status")
    source = anilist.get("source")

    meta_parts = []
    if eps:
        meta_parts.append(f"{eps} episode{'s' if eps != 1 else ''}")
    if dur:
        meta_parts.append(f"{dur}-minute")
    if fmt:
        fmt_map = {"TV": "TV anime", "TV_SHORT": "TV Short", "MOVIE": "Movie", "SPECIAL": "Special",
                    "OVA": "OVA", "ONA": "ONA", "MUSIC": "Music"}
        meta_parts.append(fmt_map.get(fmt, fmt))

    if meta_parts:
        lines.append(f"📺 {', '.join(meta_parts)}")

    # Airing dates
    start = anilist.get("startDate", {})
    end = anilist.get("endDate", {})

    def fmt_date(d):
        if not d or not d.get("year"):
            return None
        parts = [str(d["year"])]
        if d.get("month"):
            parts.append(str(d["month"]))
            if d.get("day"):
                parts.append(str(d["day"]))
        return "-".join(parts)

    start_str = fmt_date(start)
    end_str = fmt_date(end)
    if start_str:
        air_line = f"📅 Airing from {start_str}"
        if end_str:
            air_line += f" to {end_str}"
        lines.append(air_line)

    # Season
    if season and season_year:
        season_map = {"WINTER": "Winter", "SPRING": "Spring", "SUMMER": "Summer", "FALL": "Fall"}
        lines.append(f"🌤 {season_map.get(season, season)} {season_year}")

    # Similarity
    lines.append(f"🤨 <b>Похоже на:</b> <code>{similarity * 100:.1f}%</code>")

    # Episode
    if episode is not None:
        lines.append(f"🍿 <b>Эпизод:</b> <code>{episode}</code>")

    # Timestamp
    if from_time is not None:
        lines.append(f"⏱ {fmt_time(from_time)} — {fmt_time(to_time)}")

    # Genres
    genres = anilist.get("genres", [])
    if genres:
        lines.append(f"🎭 <b>Genre:</b> {', '.join(genres)}")

    # Source
    if source:
        src_map = {"ORIGINAL": "Original", "MANGA": "Manga", "LIGHT_NOVEL": "Light Novel",
                    "VISUAL_NOVEL": "Visual Novel", "VIDEO_GAME": "Video Game",
                    "OTHER": "Other", "NOVEL": "Novel", "DOUJINSHI": "Doujinshi",
                    "ANIME": "Anime", "WEB_NOVEL": "Web Novel"}
        lines.append(f"📖 <b>Source:</b> {src_map.get(source, source)}")

    # Studios
    studios_edges = anilist.get("studios", {}).get("edges", [])
    if studios_edges:
        main = [e["node"]["name"] for e in studios_edges if e.get("isMain")]
        other = [e["node"]["name"] for e in studios_edges if not e.get("isMain")]
        if main:
            lines.append(f"🎨 <b>Studio:</b> {', '.join(main)}")
        if other:
            lines.append(f"🎬 <b>Producers:</b> {', '.join(other)}")

    # Filename (original file matched)
    if filename:
        lines.append(f"📁 <code>{filename}</code>")

    # External links
    site_url = anilist.get("siteUrl")
    ext_links = anilist.get("externalLinks", [])
    links = []
    if site_url:
        links.append(f'<a href="{site_url}">AniList</a>')
    for el in ext_links:
        url = el.get("url")
        site = el.get("site", "Link")
        if url:
            links.append(f'<a href="{url}">{site}</a>')
    if links:
        lines.append(f"🔗 {' • '.join(links)}")

    # Cover image
    cover = anilist.get("coverImage", {}).get("large")

    return "\n".join(lines), cover


@loader.tds
class animetoolsMod(loader.Module):
    """FindAnime"""

    strings = {
        "name": "FindAnime",
        "no_results": "<emoji document_id=5210952531676504517>❌</emoji> Результатов не найдено!",
        "loading": "<emoji document_id=5213452215527677338>⏳</emoji> Загрузка ...",
        "error": "<emoji document_id=5215273032553078755>❎</emoji> Произошла ошибка, попробуйте снова",
        "reply": "<emoji document_id=5215273032553078755>❌</emoji> Нужно ответить на фото/видео или прикрепить его!",
        "_cmd_doc_findanime": "Ищет по картинке что за аниме",
    }

    @loader.command(alias="fa")
    async def findanimecmd(self, message):
        """Search by picture for what anime"""
        loading = await utils.answer(message, self.strings["loading"])
        reply_msg = await message.get_reply_message()
        msg = reply_msg or message
        media = msg.media

        if not media:
            return await utils.answer(message, self.strings["reply"])

        if msg.photo:
            filename = "photo.png"
        elif msg.video:
            filename = "video.mp4"
        elif msg.gif:
            filename = "gif.gif"
        else:
            filename = "photo.png"

        filename = await self.client.download_media(media, file=filename)
        typem, encoding = mimetypes.guess_type(filename)

        try:
            r = requests.post(
                "https://api.trace.moe/search?anilistInfo",
                data=open(filename, "rb"),
                headers={"Content-Type": typem},
                timeout=15,
            ).json()
        except Exception as e:
            await loading.delete()
            return await utils.answer(message, self.strings["error"])
        finally:
            if os.path.exists(filename):
                os.remove(filename)

        if r.get("error"):
            await loading.delete()
            return await utils.answer(message, f"❎ trace.moe: {r['error']}")

        if not r.get("result"):
            await loading.delete()
            return await utils.answer(message, self.strings["no_results"])

        res = r["result"][0]
        caption, cover_url = format_anime_card(res)
        video = res.get("video")

        await loading.delete()

        # Try to send with video preview, fallback to text
        if video:
            await utils.answer_file(message, file=video, caption=caption)
        elif cover_url:
            await utils.answer_file(message, file=cover_url, caption=caption)
        else:
            await utils.answer(message, caption)