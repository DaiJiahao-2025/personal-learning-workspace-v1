import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.models import Transcript, TranscriptSegment
from backend.app.subtitles import (
    SubtitleBlockedError,
    _pick_bilibili_cid,
    _pick_bilibili_track,
    fetch_youtube_transcript,
)
from backend.app.transcript_cache import (
    build_bilibili_cache_key,
    load_bilibili_transcript,
    save_bilibili_transcript,
)


class SubtitleTests(unittest.TestCase):
    def test_pick_bilibili_track_prefers_manual_chinese(self) -> None:
        tracks = [
            {"lan": "en", "subtitle_url": "en"},
            {"lan": "ai-zh", "ai_type": 1, "subtitle_url": "ai"},
            {"lan": "zh-CN", "ai_type": 0, "subtitle_url": "manual"},
        ]
        self.assertEqual(_pick_bilibili_track(tracks), tracks[2])

    def test_pick_bilibili_cid_uses_requested_page(self) -> None:
        payload = {"data": {"pages": [{"cid": 11}, {"cid": 22}], "cid": 11}}
        self.assertEqual(_pick_bilibili_cid(payload, 2), 22)
        self.assertIsNone(_pick_bilibili_cid(payload, 3))

    def test_cache_key_keeps_pages_separate(self) -> None:
        self.assertNotEqual(
            build_bilibili_cache_key("BV1", 1),
            build_bilibili_cache_key("BV1", 2),
        )

    def test_transcript_cache_round_trip(self) -> None:
        transcript = Transcript(
            language="zh",
            full_text="测试",
            segments=[TranscriptSegment(start=0, end=1, text="测试")],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            with patch("backend.app.transcript_cache.TRANSCRIPT_CACHE_DIR", cache_dir):
                save_bilibili_transcript("BV1", 1, transcript)
                loaded = load_bilibili_transcript("BV1", 1)

        self.assertEqual(loaded, transcript)

    def test_youtube_blocked_error_is_distinct(self) -> None:
        class BrokenApi:
            def list(self, _video_id: str):
                raise Exception("Too Many Requests")

        with patch("backend.app.subtitles._build_youtube_api", return_value=BrokenApi()):
            with self.assertRaises(SubtitleBlockedError):
                fetch_youtube_transcript("https://www.youtube.com/watch?v=dyTIt1HQ_aw")


if __name__ == "__main__":
    unittest.main()
