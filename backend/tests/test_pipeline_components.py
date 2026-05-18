import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.downloaders import get_downloader
from backend.app.downloaders.bilibili import BilibiliDownloader
from backend.app.downloaders.youtube import YouTubeDownloader
from backend.app.gpt.request_chunker import RequestChunker
from backend.app.models import (
    TaskStatus,
    Transcript,
    TranscriptSegment,
    TranscriptionConfig,
    VideoNoteRequest,
)
from backend.app.storage import create_task_record, get_task_snapshot, init_db, update_task_status
from backend.app.subtitles import SubtitleUnavailableError
from backend.app.transcribers.groq import GroqTranscriber
from backend.app.transcribers.local_whisper import LocalWhisperTranscriber
from backend.app.transcribers.openai_compatible import OpenAICompatibleTranscriber
from backend.app.transcribers.provider import get_transcriber


class PipelineComponentTests(unittest.TestCase):
    def test_downloader_registry_returns_supported_platforms(self) -> None:
        self.assertEqual(get_downloader("bilibili").platform, "bilibili")
        self.assertEqual(get_downloader("youtube").platform, "youtube")

    def test_transcriber_factory_routes_providers(self) -> None:
        config = TranscriptionConfig()
        self.assertIsInstance(get_transcriber(config), LocalWhisperTranscriber)
        self.assertIsInstance(
            get_transcriber(config.model_copy(update={"provider": "openai_compatible"})),
            OpenAICompatibleTranscriber,
        )
        self.assertIsInstance(
            get_transcriber(config.model_copy(update={"provider": "groq"})),
            GroqTranscriber,
        )

    def test_chunker_preserves_order_and_splits_oversized_segments(self) -> None:
        segments = [
            TranscriptSegment(start=0, end=1, text="aaaa"),
            TranscriptSegment(start=1, end=2, text="bbbb"),
            TranscriptSegment(start=2, end=3, text="cccccccc"),
        ]
        chunks = RequestChunker(max_chars=6).chunk_segments(segments)
        combined = "".join(segment.text for chunk in chunks for segment in chunk.segments)
        self.assertEqual(combined, "aaaabbbbcccccccc")
        self.assertGreaterEqual(len(chunks), 3)

    def test_sqlite_task_state_round_trip(self) -> None:
        request = VideoNoteRequest(
            videoUrl="https://www.youtube.com/watch?v=abc123",
            platform="youtube",
            style="minimal",
        )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "backend.app.storage.DB_PATH",
            Path(temp_dir) / "tasks.sqlite3",
        ):
            init_db()
            create_task_record("task-1", request)
            update_task_status("task-1", TaskStatus.SUMMARIZING)
            snapshot = get_task_snapshot("task-1")

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.status, TaskStatus.SUMMARIZING)
        self.assertEqual(snapshot.platform, "youtube")

    def test_bilibili_downloader_uses_subtitle_fallback_before_audio(self) -> None:
        transcript = Transcript(
            language="zh",
            full_text="瀛楀箷",
            segments=[TranscriptSegment(start=0, end=1, text="瀛楀箷")],
        )

        async def fake_download_subtitles(*_args, **_kwargs):
            return transcript

        with patch(
            "backend.app.downloaders.bilibili.fetch_bilibili_transcript",
            side_effect=SubtitleUnavailableError("no direct subtitle"),
        ), patch(
            "backend.app.downloaders.bilibili.download_subtitles",
            fake_download_subtitles,
        ):
            result = asyncio.run(
                BilibiliDownloader().fetch_transcript("https://www.bilibili.com/video/BV1")
            )

        self.assertEqual(result, transcript)

    def test_youtube_downloader_uses_subtitle_fallback_before_audio(self) -> None:
        transcript = Transcript(
            language="en",
            full_text="subtitle",
            segments=[TranscriptSegment(start=0, end=1, text="subtitle")],
        )

        async def fake_download_subtitles(*_args, **_kwargs):
            return transcript

        with patch(
            "backend.app.downloaders.youtube.fetch_youtube_transcript",
            side_effect=SubtitleUnavailableError("no direct subtitle"),
        ), patch(
            "backend.app.downloaders.youtube.download_subtitles",
            fake_download_subtitles,
        ):
            result = asyncio.run(
                YouTubeDownloader().fetch_transcript("https://www.youtube.com/watch?v=abc123")
            )

        self.assertEqual(result, transcript)
