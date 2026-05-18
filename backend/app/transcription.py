from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import httpx
import yt_dlp

from .config_store import get_effective_bilibili_cookie, get_effective_proxy_url
from .models import Transcript, TranscriptSegment, TranscriptionConfig


class TranscriptionError(RuntimeError):
    """Raised when no usable transcript can be produced through cloud transcription."""


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


def _download_audio(video_url: str, platform: str, directory: Path) -> Path:
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
        downloader.extract_info(video_url, download=True)

    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.name != "bilibili-cookies.txt"
    ]
    if not candidates:
        raise TranscriptionError("未能下载可用于转写的音频")

    return max(candidates, key=lambda path: path.stat().st_size)


async def transcribe_video(video_url: str, platform: str, config: TranscriptionConfig) -> Transcript:
    if not config.base_url.strip() or not config.api_key.strip() or not config.model_name.strip():
        raise TranscriptionError("请先完成转写配置")

    with tempfile.TemporaryDirectory(prefix="learnflow-audio-") as temp_dir:
        audio_path = _download_audio(video_url, platform, Path(temp_dir))

        endpoint = f"{config.base_url.rstrip('/')}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {config.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                with audio_path.open("rb") as audio_file:
                    response = await client.post(
                        endpoint,
                        headers=headers,
                        data={"model": config.model_name},
                        files={"file": (audio_path.name, audio_file, "application/octet-stream")},
                    )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise TranscriptionError("云端转写服务返回异常") from exc
        except Exception as exc:  # noqa: BLE001
            raise TranscriptionError("云端转写失败") from exc

    text = str(payload.get("text") or "").strip()
    if not text:
        raise TranscriptionError("云端转写结果为空")

    return Transcript(
        language=str(payload.get("language") or "unknown"),
        full_text=text,
        segments=[TranscriptSegment(start=0, end=0, text=text)],
    )
