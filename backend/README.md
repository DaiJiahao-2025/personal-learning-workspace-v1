# Video Notes Backend

The backend now runs as an explicit pipeline:

```text
Downloader -> Transcript/Audio -> Transcriber -> Chunker -> Summarizer -> SQLite storage
```

## Run locally

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8483 --reload
```

## Current capabilities

- Bilibili and YouTube downloader adapters behind one registry
- Native subtitle-first ingestion with layered fallback (`player API` / platform API -> `yt-dlp` subtitle download), and audio extraction only after subtitle paths are exhausted
- STT provider factory with `local_whisper`, `openai_compatible`, and `groq`
- Chunked long-form summarization with structured note output plus rendered Markdown
- SQLite-backed task, transcript, and note persistence
- Bounded in-process task concurrency controlled by `TASK_MAX_CONCURRENCY`

## Main API

- `POST /api/video-notes`
- `GET /api/video-notes/{task_id}`
- `GET/PUT /api/transcription-config`

`POST /api/video-notes` accepts `videoUrl`, `platform`, `style`, and optional `sttProvider`.
