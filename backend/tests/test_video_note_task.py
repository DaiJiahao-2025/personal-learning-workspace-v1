import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.models import (
    AiConfig,
    LearningNote,
    NoteChapter,
    TaskStatus,
    Transcript,
    TranscriptSegment,
    TranscriptionConfig,
    VideoNoteRequest,
)
from backend.app.storage import init_db
from backend.app.tasks import create_task, get_task, run_video_note_task


class FakeDownloader:
    platform = "bilibili"

    def __init__(self, transcript: Transcript | None) -> None:
        self.transcript = transcript
        self.audio_extracted = False

    async def fetch_transcript(self, _video_url: str) -> Transcript | None:
        return self.transcript

    async def extract_audio(self, _video_url: str, directory: Path):
        self.audio_extracted = True
        audio_path = directory / "demo.wav"
        audio_path.write_bytes(b"audio")

        class Audio:
            file_path = str(audio_path)

        return Audio()


class FakeTranscriber:
    async def transcribe(self, _audio_path: Path) -> Transcript:
        return Transcript(
            language="zh",
            full_text="来自转写",
            segments=[TranscriptSegment(start=0, end=1, text="来自转写")],
        )


class VideoNoteTaskTests(unittest.TestCase):
    def _request(self) -> VideoNoteRequest:
        return VideoNoteRequest(
            videoUrl="https://www.bilibili.com/video/BV1xx411c7mD",
            platform="bilibili",
            style="minimal",
        )

    def _note(self) -> LearningNote:
        return LearningNote(
            title="测试标题",
            summary="测试摘要",
            chapters=[NoteChapter(title="章节", summary="内容", start=0, end=1)],
            keyPoints=["要点"],
            actionItems=["复习"],
            references=[],
        )

    def test_task_reaches_success_when_subtitle_and_summary_exist(self) -> None:
        transcript = Transcript(
            language="zh",
            full_text="测试字幕",
            segments=[TranscriptSegment(start=0, end=1, text="测试字幕")],
        )
        downloader = FakeDownloader(transcript)

        async def fake_summarize(*_args, **_kwargs):
            return self._note(), "# 测试标题"

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "backend.app.storage.DB_PATH",
            Path(temp_dir) / "tasks.sqlite3",
        ):
            init_db()
            request = self._request()
            task_id = create_task(request)
            with patch("backend.app.tasks.get_downloader", return_value=downloader), patch(
                "backend.app.tasks.load_ai_config",
                return_value=AiConfig(baseUrl="https://example.com/v1", apiKey="secret", modelName="demo"),
            ), patch("backend.app.tasks.summarize_transcript", fake_summarize):
                asyncio.run(run_video_note_task(task_id, request))

            task = get_task(task_id)

        self.assertIsNotNone(task)
        self.assertEqual(task.status, TaskStatus.SUCCESS)
        self.assertEqual(task.note.title, "测试标题")
        self.assertFalse(downloader.audio_extracted)

    def test_task_falls_back_to_transcription_when_subtitle_is_unavailable(self) -> None:
        downloader = FakeDownloader(None)

        async def fake_summarize(*_args, **_kwargs):
            return self._note(), "# 测试标题"

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "backend.app.storage.DB_PATH",
            Path(temp_dir) / "tasks.sqlite3",
        ):
            init_db()
            request = self._request()
            task_id = create_task(request)
            with patch("backend.app.tasks.get_downloader", return_value=downloader), patch(
                "backend.app.tasks.load_transcription_config",
                return_value=TranscriptionConfig(),
            ), patch("backend.app.tasks.get_transcriber", return_value=FakeTranscriber()), patch(
                "backend.app.tasks.load_ai_config",
                return_value=AiConfig(baseUrl="https://example.com/v1", apiKey="secret", modelName="demo"),
            ), patch("backend.app.tasks.summarize_transcript", fake_summarize):
                asyncio.run(run_video_note_task(task_id, request))

            task = get_task(task_id)

        self.assertIsNotNone(task)
        self.assertEqual(task.status, TaskStatus.SUCCESS)
        self.assertEqual(task.transcript_source, "speech_to_text")
        self.assertTrue(downloader.audio_extracted)
