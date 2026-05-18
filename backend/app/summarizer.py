from __future__ import annotations

import json
import re

import httpx

from .gpt.prompt_builder import build_chunk_messages, build_merge_messages
from .gpt.request_chunker import RequestChunker
from .models import AiConfig, LearningNote, Transcript


class AiConfigError(RuntimeError):
    """Raised when the local AI config is incomplete."""


class SummarizationError(RuntimeError):
    """Raised when the upstream AI provider cannot return a usable summary."""


def _strip_code_fence(content: str) -> str:
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content.strip(), re.DOTALL)
    return fenced.group(1).strip() if fenced else content.strip()


def _parse_note_payload(content: str) -> dict:
    try:
        payload = json.loads(_strip_code_fence(content))
    except json.JSONDecodeError as exc:
        raise SummarizationError("AI 返回的结构化结果不是合法 JSON") from exc
    if not isinstance(payload, dict):
        raise SummarizationError("AI 返回的结构化结果格式不正确")
    return payload


async def _chat(messages: list[dict[str, str]], config: AiConfig) -> dict:
    endpoint = f"{config.base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": config.model_name,
        "temperature": 0.2,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise SummarizationError(f"AI 服务返回错误：{exc.response.status_code}") from exc
    except Exception as exc:  # noqa: BLE001
        raise SummarizationError("调用 AI 服务失败") from exc

    choices = data.get("choices") or []
    content = (((choices[0] if choices else {}).get("message") or {}).get("content") or "").strip()
    if not content:
        raise SummarizationError("AI 服务未返回可用结果")
    return _parse_note_payload(content)


def render_markdown(note: LearningNote) -> str:
    lines = [f"# {note.title}", "", "## 摘要", note.summary]

    if note.chapters:
        lines.extend(["", "## 章节"])
        for chapter in note.chapters:
            lines.append(f"### {chapter.title}")
            lines.append(chapter.summary)

    if note.key_points:
        lines.extend(["", "## 关键要点"])
        lines.extend(f"- {item}" for item in note.key_points)

    if note.action_items:
        lines.extend(["", "## 行动项"])
        lines.extend(f"- {item}" for item in note.action_items)

    if note.references:
        lines.extend(["", "## 引用时间点"])
        lines.extend(
            f"- {reference.timestamp:.1f}s：{reference.label}" for reference in note.references
        )

    return "\n".join(lines).strip()


async def summarize_transcript(
    transcript: Transcript,
    style: str,
    config: AiConfig,
    *,
    max_chunk_chars: int = 12_000,
) -> tuple[LearningNote, str]:
    if not config.base_url.strip() or not config.api_key.strip() or not config.model_name.strip():
        raise AiConfigError("请先在设置页完成 AI 生成配置")

    chunks = RequestChunker(max_chars=max_chunk_chars).chunk_segments(transcript.segments)
    if not chunks:
        raise SummarizationError("字幕内容为空，无法生成笔记")

    partials = [
        await _chat(build_chunk_messages(chunk.segments, style), config)
        for chunk in chunks
    ]
    merged_payload = (
        partials[0]
        if len(partials) == 1
        else await _chat(build_merge_messages(partials, style), config)
    )

    try:
        note = LearningNote.model_validate(merged_payload)
    except Exception as exc:  # noqa: BLE001
        raise SummarizationError("AI 返回的学习笔记结构不完整") from exc
    return note, render_markdown(note)
