from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from .config_store import load_ai_config, load_transcription_config
from .downloaders import get_downloader
from .models import TaskSnapshot, TaskStatus, VideoNoteRequest
from .storage import (
    create_task_record,
    get_task_snapshot,
    save_note,
    save_transcript,
    update_task_status,
)
from .summarizer import AiConfigError, SummarizationError, summarize_transcript
from .transcribers import get_transcriber


TASK_MAX_CONCURRENCY = max(1, int(os.getenv("TASK_MAX_CONCURRENCY", "2")))
TASK_SEMAPHORE = asyncio.Semaphore(TASK_MAX_CONCURRENCY)


def create_task(request: VideoNoteRequest) -> str:
    task_id = str(uuid4())
    create_task_record(task_id, request)
    return task_id


def get_task(task_id: str) -> TaskSnapshot | None:
    return get_task_snapshot(task_id)


async def run_video_note_task(task_id: str, request: VideoNoteRequest) -> None:
    async with TASK_SEMAPHORE:
        try:
            downloader = get_downloader(request.platform)
            update_task_status(task_id, TaskStatus.FETCHING_SUBTITLE)
            transcript = await downloader.fetch_transcript(str(request.video_url))
            if transcript is not None:
                transcript = transcript.model_copy(update={"source": "native_subtitle"})

            if transcript is None:
                update_task_status(task_id, TaskStatus.EXTRACTING_AUDIO)
                with tempfile.TemporaryDirectory(prefix="learnflow-audio-") as temp_dir:
                    audio = await downloader.extract_audio(str(request.video_url), Path(temp_dir))
                    update_task_status(task_id, TaskStatus.TRANSCRIBING)
                    transcription_config = load_transcription_config()
                    transcriber = get_transcriber(transcription_config, request.stt_provider)
                    transcript = await transcriber.transcribe(Path(audio.file_path))
                    transcript = transcript.model_copy(update={"source": "speech_to_text"})

            save_transcript(task_id, transcript)
            update_task_status(task_id, TaskStatus.CHUNKING)
            update_task_status(task_id, TaskStatus.SUMMARIZING)
            note, markdown = await summarize_transcript(transcript, request.style, load_ai_config())
            save_note(task_id, note, markdown)
            update_task_status(task_id, TaskStatus.SUCCESS)
        except (AiConfigError, SummarizationError, RuntimeError, ValueError) as exc:
            update_task_status(task_id, TaskStatus.FAILED, str(exc))
        except Exception:  # noqa: BLE001
            update_task_status(task_id, TaskStatus.FAILED, "生成笔记失败，请稍后重试")
