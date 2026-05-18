from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile

from ..models import AudioAsset, Transcript
from ..subtitles import SubtitleUnavailableError, fetch_youtube_transcript
from .base import BaseDownloader
from .common import download_audio, download_subtitles


class YouTubeDownloader(BaseDownloader):
    platform = "youtube"

    async def fetch_transcript(self, video_url: str) -> Transcript | None:
        try:
            return await asyncio.to_thread(fetch_youtube_transcript, video_url)
        except SubtitleUnavailableError:
            try:
                with tempfile.TemporaryDirectory(prefix="learnflow-subtitle-") as temp_dir:
                    return await download_subtitles(
                        video_url,
                        self.platform,
                        Path(temp_dir),
                        ["zh-Hans", "zh", "zh-CN", "zh-TW", "en", "en-US", "ja"],
                    )
            except Exception:  # noqa: BLE001
                return None

    async def extract_audio(self, video_url: str, directory: Path) -> AudioAsset:
        return await download_audio(video_url, self.platform, directory)
