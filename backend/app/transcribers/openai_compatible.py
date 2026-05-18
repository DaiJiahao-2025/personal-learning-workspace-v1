from __future__ import annotations

from pathlib import Path

import httpx

from ..models import Transcript, TranscriptSegment, TranscriptionConfig
from .base import BaseTranscriber


class OpenAICompatibleTranscriber(BaseTranscriber):
    def __init__(self, config: TranscriptionConfig) -> None:
        self.config = config

    async def transcribe(self, audio_path: Path) -> Transcript:
        if (
            not self.config.base_url.strip()
            or not self.config.api_key.strip()
            or not self.config.model_name.strip()
        ):
            raise RuntimeError("请先完成云端转写配置")

        endpoint = f"{self.config.base_url.rstrip('/')}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.config.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                with audio_path.open("rb") as audio_file:
                    response = await client.post(
                        endpoint,
                        headers=headers,
                        data={"model": self.config.model_name},
                        files={"file": (audio_path.name, audio_file, "application/octet-stream")},
                    )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError("云端转写服务返回异常") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("云端转写失败") from exc

        text = str(payload.get("text") or "").strip()
        if not text:
            raise RuntimeError("云端转写结果为空")

        return Transcript(
            language=str(payload.get("language") or "unknown"),
            full_text=text,
            segments=[TranscriptSegment(start=0, end=0, text=text)],
        )
