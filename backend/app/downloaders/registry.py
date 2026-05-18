from __future__ import annotations

from .base import BaseDownloader
from .bilibili import BilibiliDownloader
from .youtube import YouTubeDownloader


_DOWNLOADERS: dict[str, BaseDownloader] = {
    "bilibili": BilibiliDownloader(),
    "youtube": YouTubeDownloader(),
}


def get_downloader(platform: str) -> BaseDownloader:
    try:
        return _DOWNLOADERS[platform]
    except KeyError as exc:
        raise ValueError(f"不支持的平台：{platform}") from exc
