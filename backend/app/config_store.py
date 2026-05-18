from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypeVar

from .models import AiConfig, DownloaderConfig, TranscriptionConfig


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AI_CONFIG_PATH = DATA_DIR / "ai_config.json"
DOWNLOADER_CONFIG_PATH = DATA_DIR / "downloader_config.json"
TRANSCRIPTION_CONFIG_PATH = DATA_DIR / "transcription_config.json"


TModel = TypeVar("TModel", AiConfig, DownloaderConfig, TranscriptionConfig)


def _load_json_model(path: Path, model_type: type[TModel]) -> TModel:
    if not path.exists():
        return model_type()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return model_type.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError):
        return model_type()


def _save_json_model(path: Path, config: TModel) -> TModel:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.model_dump(by_alias=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config


def load_ai_config() -> AiConfig:
    return _load_json_model(AI_CONFIG_PATH, AiConfig)


def save_ai_config(config: AiConfig) -> AiConfig:
    return _save_json_model(AI_CONFIG_PATH, config)


def load_downloader_config() -> DownloaderConfig:
    return _load_json_model(DOWNLOADER_CONFIG_PATH, DownloaderConfig)


def save_downloader_config(config: DownloaderConfig) -> DownloaderConfig:
    return _save_json_model(DOWNLOADER_CONFIG_PATH, config)


def update_bilibili_cookie(cookie: str) -> DownloaderConfig:
    config = load_downloader_config()
    if not cookie or cookie == config.bilibili_cookie:
        return config

    config = config.model_copy(update={"bilibili_cookie": cookie})
    return save_downloader_config(config)


def get_effective_proxy_url() -> str:
    config = load_downloader_config()
    if config.proxy_url.strip():
        return config.proxy_url.strip()

    for key in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        value = os.environ.get(key, "").strip()
        if value:
            return value

    return ""


def get_effective_bilibili_cookie() -> str:
    config = load_downloader_config()
    if config.bilibili_cookie.strip():
        return config.bilibili_cookie.strip()
    return os.environ.get("BILIBILI_COOKIE", "").strip()


def load_transcription_config() -> TranscriptionConfig:
    return _load_json_model(TRANSCRIPTION_CONFIG_PATH, TranscriptionConfig)


def save_transcription_config(config: TranscriptionConfig) -> TranscriptionConfig:
    return _save_json_model(TRANSCRIPTION_CONFIG_PATH, config)
