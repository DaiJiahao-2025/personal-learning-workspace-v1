from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile

from ..models import AudioAsset, Transcript
from ..subtitles import SubtitleBlockedError, SubtitleUnavailableError, fetch_youtube_transcript
from .base import BaseDownloader
from .common import download_audio, download_subtitles


class YouTubeDownloader(BaseDownloader):
    platform = "youtube"

    @staticmethod
    def _is_blocked_error(error: Exception) -> bool:
        message = str(error).lower()
        return any(
            marker in message
            for marker in ("403", "429", "forbidden", "too many requests", "rate limit", "blocked")
        )

    async def fetch_transcript(self, video_url: str) -> Transcript | None:
        try:
            return await asyncio.to_thread(fetch_youtube_transcript, video_url)
        except SubtitleBlockedError:
            raise
        except SubtitleUnavailableError:
            try:
                with tempfile.TemporaryDirectory(prefix="learnflow-subtitle-") as temp_dir:
                    return await download_subtitles(
                        video_url,
                        self.platform,
                        Path(temp_dir),
                        ["zh-Hans", "zh", "zh-CN", "zh-TW", "en", "en-US", "ja"],
                    )
            except Exception as exc:  # noqa: BLE001
                if self._is_blocked_error(exc):
                    raise SubtitleBlockedError("YouTube 字幕请求被阻止，请检查代理或稍后重试") from exc
                return None

    async def extract_audio(self, video_url: str, directory: Path) -> AudioAsset:
        return await download_audio(video_url, self.platform, directory)
