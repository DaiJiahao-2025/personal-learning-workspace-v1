from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import AudioAsset, Transcript


class BaseDownloader(ABC):
    platform: str

    @abstractmethod
    async def fetch_transcript(self, video_url: str) -> Transcript | None:
        """Return a native subtitle transcript when the platform exposes one."""

    @abstractmethod
    async def extract_audio(self, video_url: str, directory: Path) -> AudioAsset:
        """Download or extract audio into `directory` and return local media metadata."""
