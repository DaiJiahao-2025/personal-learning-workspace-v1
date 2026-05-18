from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    FETCHING_SUBTITLE = "FETCHING_SUBTITLE"
    EXTRACTING_AUDIO = "EXTRACTING_AUDIO"
    TRANSCRIBING = "TRANSCRIBING"
    CHUNKING = "CHUNKING"
    SUMMARIZING = "SUMMARIZING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AiConfig(BaseModel):
    base_url: str = Field(default="", alias="baseUrl")
    api_key: str = Field(default="", alias="apiKey")
    model_name: str = Field(default="", alias="modelName")

    model_config = {"populate_by_name": True}


class DownloaderConfig(BaseModel):
    bilibili_cookie: str = Field(default="", alias="bilibiliCookie")
    proxy_url: str = Field(default="", alias="proxyUrl")

    model_config = {"populate_by_name": True}


class TranscriptionConfig(BaseModel):
    provider: Literal["local_whisper", "openai_compatible", "groq"] = Field(
        default="local_whisper"
    )
    base_url: str = Field(default="", alias="baseUrl")
    api_key: str = Field(default="", alias="apiKey")
    model_name: str = Field(default="", alias="modelName")
    local_model_size: str = Field(default="base", alias="localModelSize")
    local_device: str = Field(default="cpu", alias="localDevice")

    model_config = {"populate_by_name": True}


class VideoNoteRequest(BaseModel):
    video_url: HttpUrl = Field(alias="videoUrl")
    platform: Literal["bilibili", "youtube"]
    style: Literal["minimal", "detailed"] = "minimal"
    stt_provider: Literal["local_whisper", "openai_compatible", "groq"] | None = Field(
        default=None,
        alias="sttProvider",
    )

    model_config = {"populate_by_name": True}


class TaskResponse(BaseModel):
    task_id: str = Field(alias="taskId")

    model_config = {"populate_by_name": True}


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


TranscriptSource = Literal["native_subtitle", "speech_to_text"]


class Transcript(BaseModel):
    language: str
    full_text: str
    segments: list[TranscriptSegment]
    source: TranscriptSource | None = None


class AudioAsset(BaseModel):
    file_path: str = Field(alias="filePath")
    title: str
    duration: float = 0
    platform: Literal["bilibili", "youtube"]
    video_id: str = Field(alias="videoId")

    model_config = {"populate_by_name": True}


class NoteChapter(BaseModel):
    title: str
    summary: str
    start: float | None = None
    end: float | None = None


class NoteReference(BaseModel):
    timestamp: float
    label: str


class LearningNote(BaseModel):
    title: str
    summary: str
    chapters: list[NoteChapter] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list, alias="keyPoints")
    action_items: list[str] = Field(default_factory=list, alias="actionItems")
    references: list[NoteReference] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class TaskSnapshot(BaseModel):
    task_id: str = Field(alias="taskId")
    status: TaskStatus
    platform: Literal["bilibili", "youtube"] | None = None
    style: Literal["minimal", "detailed"] | None = None
    stt_provider: Literal["local_whisper", "openai_compatible", "groq"] | None = Field(
        default=None,
        alias="sttProvider",
    )
    transcript_source: TranscriptSource | None = Field(default=None, alias="transcriptSource")
    markdown: str | None = None
    note: LearningNote | None = None
    message: str | None = None

    model_config = {"populate_by_name": True}


class BilibiliPrefetchRequest(BaseModel):
    video_url: HttpUrl = Field(alias="videoUrl")
    bvid: str
    page: int = Field(default=1, ge=1)
    cookie: str = ""
    transcript: Transcript | None = None

    model_config = {"populate_by_name": True}
