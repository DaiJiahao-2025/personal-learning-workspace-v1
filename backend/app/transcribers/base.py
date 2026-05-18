from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Transcript


class BaseTranscriber(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path) -> Transcript:
        """Return a transcript for the provided local audio file."""
