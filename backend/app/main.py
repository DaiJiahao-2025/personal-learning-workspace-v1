from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config_store import (
    load_ai_config,
    load_downloader_config,
    load_transcription_config,
    save_ai_config,
    save_downloader_config,
    save_transcription_config,
    update_bilibili_cookie,
)
from .models import (
    AiConfig,
    BilibiliPrefetchRequest,
    DownloaderConfig,
    TaskResponse,
    TaskSnapshot,
    TranscriptionConfig,
    VideoNoteRequest,
)
from .storage import init_db
from .tasks import create_task, get_task, run_video_note_task
from .transcript_cache import save_bilibili_transcript


app = FastAPI(title="LearnFlow Video Notes API")
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"chrome-extension://.*",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ai-config", response_model=AiConfig)
def get_ai_config() -> AiConfig:
    return load_ai_config()


@app.put("/api/ai-config", response_model=AiConfig)
def update_ai_config(config: AiConfig) -> AiConfig:
    return save_ai_config(config)


@app.get("/api/downloader-config", response_model=DownloaderConfig)
def get_downloader_config() -> DownloaderConfig:
    return load_downloader_config()


@app.put("/api/downloader-config", response_model=DownloaderConfig)
def update_downloader_config(config: DownloaderConfig) -> DownloaderConfig:
    return save_downloader_config(config)


@app.get("/api/transcription-config", response_model=TranscriptionConfig)
def get_transcription_config() -> TranscriptionConfig:
    return load_transcription_config()


@app.put("/api/transcription-config", response_model=TranscriptionConfig)
def update_transcription_config(config: TranscriptionConfig) -> TranscriptionConfig:
    return save_transcription_config(config)


@app.post("/api/bilibili-prefetch")
def upsert_bilibili_prefetch(payload: BilibiliPrefetchRequest) -> dict[str, str]:
    if payload.cookie:
        update_bilibili_cookie(payload.cookie)
    if payload.transcript is not None:
        save_bilibili_transcript(payload.bvid, payload.page, payload.transcript)
    return {"status": "ok"}


@app.post("/api/video-notes", response_model=TaskResponse)
def create_video_note(request: VideoNoteRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    task_id = create_task(request)
    background_tasks.add_task(run_video_note_task, task_id, request)
    return TaskResponse(taskId=task_id)


@app.get("/api/video-notes/{task_id}", response_model=TaskSnapshot)
def get_video_note(task_id: str) -> TaskSnapshot:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
