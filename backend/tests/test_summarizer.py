import asyncio
import unittest
from unittest.mock import patch

from backend.app.models import AiConfig, Transcript, TranscriptSegment
from backend.app.summarizer import summarize_transcript


class SummarizerTests(unittest.TestCase):
    def test_long_transcript_uses_chunked_summary_and_merge(self) -> None:
        transcript = Transcript(
            language="zh",
            full_text="",
            segments=[
                TranscriptSegment(start=0, end=1, text="aaaa"),
                TranscriptSegment(start=1, end=2, text="bbbb"),
                TranscriptSegment(start=2, end=3, text="cccc"),
            ],
        )
        responses = [
            {
                "title": "分段一",
                "summary": "摘要一",
                "chapters": [],
                "keyPoints": ["A"],
                "actionItems": [],
                "references": [],
            },
            {
                "title": "分段二",
                "summary": "摘要二",
                "chapters": [],
                "keyPoints": ["B"],
                "actionItems": [],
                "references": [],
            },
            {
                "title": "分段三",
                "summary": "摘要三",
                "chapters": [],
                "keyPoints": ["C"],
                "actionItems": [],
                "references": [],
            },
            {
                "title": "完整笔记",
                "summary": "合并摘要",
                "chapters": [],
                "keyPoints": ["A", "B", "C"],
                "actionItems": [],
                "references": [],
            },
        ]

        async def fake_chat(*_args, **_kwargs):
            return responses.pop(0)

        with patch("backend.app.summarizer._chat", fake_chat):
            note, markdown = asyncio.run(
                summarize_transcript(
                    transcript,
                    "minimal",
                    AiConfig(baseUrl="https://example.com/v1", apiKey="secret", modelName="demo"),
                    max_chunk_chars=6,
                )
            )

        self.assertEqual(note.title, "完整笔记")
        self.assertIn("# 完整笔记", markdown)


if __name__ == "__main__":
    unittest.main()
