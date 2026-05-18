from __future__ import annotations

from dataclasses import dataclass

from ..models import TranscriptSegment


@dataclass
class TranscriptChunk:
    segments: list[TranscriptSegment]


class RequestChunker:
    def __init__(self, max_chars: int = 12_000) -> None:
        self.max_chars = max_chars

    def chunk_segments(self, segments: list[TranscriptSegment]) -> list[TranscriptChunk]:
        chunks: list[TranscriptChunk] = []
        current: list[TranscriptSegment] = []
        current_size = 0

        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue

            if len(text) > self.max_chars:
                if current:
                    chunks.append(TranscriptChunk(current))
                    current = []
                    current_size = 0
                chunks.extend(self._split_oversized_segment(segment))
                continue

            next_size = current_size + len(text)
            if current and next_size > self.max_chars:
                chunks.append(TranscriptChunk(current))
                current = []
                current_size = 0

            current.append(segment)
            current_size += len(text)

        if current:
            chunks.append(TranscriptChunk(current))
        return chunks

    def _split_oversized_segment(self, segment: TranscriptSegment) -> list[TranscriptChunk]:
        chunks: list[TranscriptChunk] = []
        text = segment.text.strip()
        for start in range(0, len(text), self.max_chars):
            piece = text[start : start + self.max_chars]
            chunks.append(
                TranscriptChunk(
                    [
                        TranscriptSegment(
                            start=segment.start,
                            end=segment.end,
                            text=piece,
                        )
                    ]
                )
            )
        return chunks
