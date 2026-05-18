from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import yt_dlp

from ..config_store import get_effective_bilibili_cookie, get_effective_proxy_url
from ..models import AudioAsset, Transcript, TranscriptSegment


def _write_bilibili_cookie_file(cookie: str, directory: Path) -> str | None:
    if not cookie:
        return None

    cookie_path = directory / "bilibili-cookies.txt"
    lines = ["# Netscape HTTP Cookie File\n"]
    for pair in cookie.split("; "):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        lines.append(f".bilibili.com\tTRUE\t/\tFALSE\t0\t{key}\t{value}\n")
    cookie_path.write_text("".join(lines), encoding="utf-8")
    return str(cookie_path)


def _download_audio_sync(video_url: str, platform: str, directory: Path) -> AudioAsset:
    output_template = str(directory / "%(id)s.%(ext)s")
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
    }

    proxy = get_effective_proxy_url()
    if proxy:
        options["proxy"] = proxy

    if platform == "bilibili":
        options["http_headers"] = {"Referer": "https://www.bilibili.com"}
        cookie_file = _write_bilibili_cookie_file(get_effective_bilibili_cookie(), directory)
        if cookie_file:
            options["cookiefile"] = cookie_file

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(video_url, download=True)

    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.name != "bilibili-cookies.txt"
    ]
    if not candidates:
        raise RuntimeError("未能下载可用于转写的音频")

    audio_path = max(candidates, key=lambda path: path.stat().st_size)
    return AudioAsset(
        filePath=str(audio_path),
        title=str(info.get("title") or ""),
        duration=float(info.get("duration") or 0),
        platform=platform,
        videoId=str(info.get("id") or ""),
    )


async def download_audio(video_url: str, platform: str, directory: Path) -> AudioAsset:
    return await asyncio.to_thread(_download_audio_sync, video_url, platform, directory)


def _pick_requested_subtitle(
    subtitles: dict[str, dict[str, Any]],
    preferred_languages: list[str],
) -> tuple[str, dict[str, Any]] | None:
    for language in preferred_languages:
        if language in subtitles:
            return language, subtitles[language]

    for language, subtitle in subtitles.items():
        if language != "danmaku":
            return language, subtitle

    return None


def _seconds_from_timestamp(value: str) -> float:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return float(hours) * 3600 + float(minutes) * 60 + float(seconds)


def _build_transcript(language: str, segments: list[TranscriptSegment]) -> Transcript | None:
    cleaned = [segment for segment in segments if segment.text.strip()]
    if not cleaned:
        return None

    return Transcript(
        language=language,
        full_text=" ".join(segment.text for segment in cleaned),
        segments=cleaned,
    )


def _parse_bilibili_json(payload: dict[str, Any], language: str) -> Transcript | None:
    body = payload.get("body") or []
    segments = [
        TranscriptSegment(
            start=float(item.get("from", 0)),
            end=float(item.get("to", 0)),
            text=str(item.get("content") or "").strip(),
        )
        for item in body
        if str(item.get("content") or "").strip()
    ]
    return _build_transcript(language, segments)


def _parse_json3(payload: dict[str, Any], language: str) -> Transcript | None:
    segments: list[TranscriptSegment] = []
    for event in payload.get("events") or []:
        text = "".join(str(part.get("utf8") or "") for part in event.get("segs") or []).strip()
        if not text:
            continue

        start = float(event.get("tStartMs", 0)) / 1000
        duration = float(event.get("dDurationMs", 0)) / 1000
        segments.append(
            TranscriptSegment(
                start=start,
                end=start + duration,
                text=text,
            )
        )
    return _build_transcript(language, segments)


def _parse_vtt_or_srt(content: str, language: str) -> Transcript | None:
    pattern = re.compile(
        r"(?:(?:\d+)\s+)?"
        r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
        r"(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3}).*?\n"
        r"(?P<text>.*?)(?=\n{2,}|\Z)",
        re.DOTALL,
    )
    segments: list[TranscriptSegment] = []

    for match in pattern.finditer(content.replace("\r\n", "\n")):
        text = re.sub(r"<[^>]+>", "", match.group("text")).strip()
        if not text:
            continue
        segments.append(
            TranscriptSegment(
                start=_seconds_from_timestamp(match.group("start")),
                end=_seconds_from_timestamp(match.group("end")),
                text=" ".join(line.strip() for line in text.splitlines() if line.strip()),
            )
        )

    return _build_transcript(language, segments)


def _parse_subtitle_payload(payload: str, ext: str, language: str) -> Transcript | None:
    normalized_ext = ext.lower()
    if normalized_ext in {"json", "json3"}:
        data = json.loads(payload)
        if "body" in data:
            return _parse_bilibili_json(data, language)
        return _parse_json3(data, language)
    if normalized_ext in {"srt", "vtt"}:
        return _parse_vtt_or_srt(payload, language)
    return None


def _load_subtitle_file(path: Path, ext: str, language: str) -> Transcript | None:
    try:
        return _parse_subtitle_payload(path.read_text(encoding="utf-8"), ext, language)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _download_subtitles_sync(
    video_url: str,
    platform: str,
    directory: Path,
    preferred_languages: list[str],
) -> Transcript | None:
    output_template = str(directory / "%(id)s.%(ext)s")
    options: dict[str, Any] = {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": preferred_languages,
        "subtitlesformat": "json3/srt/vtt/best",
        "skip_download": True,
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
    }

    proxy = get_effective_proxy_url()
    if proxy:
        options["proxy"] = proxy

    if platform == "bilibili":
        options["http_headers"] = {"Referer": "https://www.bilibili.com"}
        cookie_file = _write_bilibili_cookie_file(get_effective_bilibili_cookie(), directory)
        if cookie_file:
            options["cookiefile"] = cookie_file

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(video_url, download=True)

    picked = _pick_requested_subtitle(info.get("requested_subtitles") or {}, preferred_languages)
    if picked is None:
        return None

    language, subtitle_info = picked
    ext = str(subtitle_info.get("ext") or "json3")
    inline_data = subtitle_info.get("data")
    if isinstance(inline_data, str) and inline_data.strip():
        try:
            transcript = _parse_subtitle_payload(inline_data, ext, language)
        except json.JSONDecodeError:
            transcript = None
        if transcript is not None:
            return transcript

    expected_file = directory / f"{info.get('id')}.{language}.{ext}"
    if expected_file.exists():
        return _load_subtitle_file(expected_file, ext, language)

    for candidate in directory.iterdir():
        if candidate.is_file() and candidate.name != "bilibili-cookies.txt":
            suffix = candidate.suffix.lstrip(".")
            transcript = _load_subtitle_file(candidate, suffix, language)
            if transcript is not None:
                return transcript

    return None


async def download_subtitles(
    video_url: str,
    platform: str,
    directory: Path,
    preferred_languages: list[str],
) -> Transcript | None:
    return await asyncio.to_thread(
        _download_subtitles_sync,
        video_url,
        platform,
        directory,
        preferred_languages,
    )
