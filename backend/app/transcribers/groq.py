from __future__ import annotations

from ..models import TranscriptionConfig
from .openai_compatible import OpenAICompatibleTranscriber


class GroqTranscriber(OpenAICompatibleTranscriber):
    def __init__(self, config: TranscriptionConfig) -> None:
        effective_config = config.model_copy(
            update={
                "base_url": config.base_url.strip() or "https://api.groq.com/openai/v1",
                "model_name": config.model_name.strip() or "whisper-large-v3-turbo",
            }
        )
        super().__init__(effective_config)
