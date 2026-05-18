from __future__ import annotations

import json
from pathlib import Path

from .config_store import DATA_DIR
from .models import Transcript


TRANSCRIPT_CACHE_DIR = DATA_DIR / "transcript_cache"


def build_bilibili_cache_key(bvid: str, page: int) -> str:
    return f"{bvid}_p{page}"


def _cache_path(bvid: str, page: int) -> Path:
    return TRANSCRIPT_CACHE_DIR / f"{build_bilibili_cache_key(bvid, page)}.json"


def load_bilibili_transcript(bvid: str, page: int) -> Transcript | None:
    path = _cache_path(bvid, page)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Transcript.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def save_bilibili_transcript(bvid: str, page: int, transcript: Transcript) -> Transcript:
    TRANSCRIPT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(bvid, page).write_text(
        json.dumps(transcript.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return transcript
