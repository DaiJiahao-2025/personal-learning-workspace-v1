from __future__ import annotations

import asyncio
from pathlib import Path

from ..models import Transcript, TranscriptSegment, TranscriptionConfig
from .base import BaseTranscriber


class LocalWhisperTranscriber(BaseTranscriber):
    def __init__(self, config: TranscriptionConfig) -> None:
        self.config = config

    async def transcribe(self, audio_path: Path) -> Transcript:
        return await asyncio.to_thread(self._transcribe_sync, audio_path)

    def _transcribe_sync(self, audio_path: Path) -> Transcript:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - depends on optional runtime install
            raise RuntimeError("本地 Whisper 未安装，请先安装 faster-whisper") from exc

        model = WhisperModel(
            self.config.local_model_size,
            device=self.config.local_device,
            compute_type="int8",
        )
        segments, info = model.transcribe(str(audio_path))

        normalized_segments = [
            TranscriptSegment(start=float(segment.start), end=float(segment.end), text=segment.text.strip())
            for segment in segments
            if segment.text.strip()
        ]
        if not normalized_segments:
            raise RuntimeError("本地 Whisper 转写结果为空")

        return Transcript(
            language=str(getattr(info, "language", "unknown") or "unknown"),
            full_text=" ".join(segment.text for segment in normalized_segments),
            segments=normalized_segments,
        )
