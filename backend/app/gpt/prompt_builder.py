from __future__ import annotations

import json

from ..models import TranscriptSegment


STYLE_GUIDANCE = {
    "minimal": "只保留最重要的概念、结论和复习要点，语言克制、简洁。",
    "detailed": "保留完整结构、关键解释和必要细节，适合后续复习。",
}


def _format_segments(segments: list[TranscriptSegment]) -> str:
    return "\n".join(f"{segment.start:.1f}s - {segment.text}" for segment in segments)


def build_chunk_messages(segments: list[TranscriptSegment], style: str) -> list[dict[str, str]]:
    schema = {
        "title": "string",
        "summary": "string",
        "chapters": [{"title": "string", "summary": "string", "start": 0, "end": 0}],
        "keyPoints": ["string"],
        "actionItems": ["string"],
        "references": [{"timestamp": 0, "label": "string"}],
    }
    return [
        {
            "role": "system",
            "content": (
                "你是学习笔记助手。只能依据提供的字幕生成内容，"
                "输出合法 JSON，不要 Markdown，不要解释。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"风格：{STYLE_GUIDANCE[style]}\n"
                f"请按这个 JSON 结构输出：{json.dumps(schema, ensure_ascii=False)}\n\n"
                "字幕如下：\n"
                f"{_format_segments(segments)}"
            ),
        },
    ]


def build_merge_messages(partials: list[dict], style: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是学习笔记助手。请把多个分段笔记合并成一个完整学习笔记，"
                "输出合法 JSON，不要 Markdown，不要解释。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"风格：{STYLE_GUIDANCE[style]}\n"
                "请合并这些分段笔记，去重但保留结构：\n"
                f"{json.dumps(partials, ensure_ascii=False)}"
            ),
        },
    ]
