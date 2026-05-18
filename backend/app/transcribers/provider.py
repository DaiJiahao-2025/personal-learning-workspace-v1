from __future__ import annotations

from ..models import TranscriptionConfig
from .base import BaseTranscriber
from .groq import GroqTranscriber
from .local_whisper import LocalWhisperTranscriber
from .openai_compatible import OpenAICompatibleTranscriber


def get_transcriber(config: TranscriptionConfig, provider_override: str | None = None) -> BaseTranscriber:
    provider = provider_override or config.provider
    if provider == "local_whisper":
        return LocalWhisperTranscriber(config)
    if provider == "openai_compatible":
        return OpenAICompatibleTranscriber(config)
    if provider == "groq":
        return GroqTranscriber(config)
    raise ValueError(f"不支持的转写器：{provider}")
