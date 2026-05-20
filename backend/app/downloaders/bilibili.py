from __future__ import annotations

from pathlib import Path
import tempfile

from ..models import AudioAsset, Transcript
from ..subtitles import SubtitleBlockedError, SubtitleUnavailableError, fetch_bilibili_transcript
from .base import BaseDownloader
from .common import download_audio, download_subtitles


class BilibiliDownloader(BaseDownloader):
    platform = "bilibili"

    @staticmethod
    def _is_blocked_error(error: Exception) -> bool:
        message = str(error).lower()
        return any(
            marker in message
            for marker in ("403", "429", "forbidden", "too many requests", "rate limit", "blocked")
        )

    async def fetch_transcript(self, video_url: str) -> Transcript | None:
        try:
            return await fetch_bilibili_transcript(video_url)
        except SubtitleBlockedError:
            raise
        except SubtitleUnavailableError:
            try:
                with tempfile.TemporaryDirectory(prefix="learnflow-subtitle-") as temp_dir:
                    return await download_subtitles(
                        video_url,
                        self.platform,
                        Path(temp_dir),
                        ["zh-Hans", "zh", "zh-CN", "ai-zh", "en", "en-US"],
                    )
            except Exception as exc:  # noqa: BLE001
                if self._is_blocked_error(exc):
                    raise SubtitleBlockedError("B 站字幕请求被阻止，请检查登录态、代理或稍后重试") from exc
                return None

    async def extract_audio(self, video_url: str, directory: Path) -> AudioAsset:
        return await download_audio(video_url, self.platform, directory)
