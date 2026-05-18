from __future__ import annotations

from typing import Any

import httpx
import requests
from youtube_transcript_api import YouTubeTranscriptApi

from .config_store import get_effective_bilibili_cookie, get_effective_proxy_url
from .models import Transcript, TranscriptSegment
from .transcript_cache import load_bilibili_transcript
from .video_links import extract_bilibili_bvid, extract_bilibili_page, extract_youtube_video_id


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class SubtitleUnavailableError(RuntimeError):
    """Raised when the current video does not expose a usable subtitle track."""


class SubtitleBlockedError(SubtitleUnavailableError):
    """Raised when an upstream subtitle provider blocks or rate-limits access."""


def _build_bilibili_headers() -> dict[str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.bilibili.com/",
    }
    cookie = get_effective_bilibili_cookie()
    if cookie:
        headers["Cookie"] = cookie
    return headers


def _pick_bilibili_track(tracks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not tracks:
        return None

    def is_chinese(track: dict[str, Any]) -> bool:
        language = str(track.get("lan") or "").lower()
        return language.startswith("zh") or language == "ai-zh"

    for track in tracks:
        if is_chinese(track) and not track.get("ai_type"):
            return track

    for track in tracks:
        if is_chinese(track):
            return track

    return tracks[0]


def _pick_bilibili_cid(view_payload: dict[str, Any], page: int) -> int | None:
    data = view_payload.get("data", {})
    pages = data.get("pages") or []
    if pages:
        if 1 <= page <= len(pages):
            return pages[page - 1].get("cid")
        return None
    return data.get("cid")


async def _resolve_bilibili_url(client: httpx.AsyncClient, video_url: str, headers: dict[str, str]) -> str:
    if "b23.tv" not in video_url:
        return video_url
    redirect_response = await client.get(video_url, headers=headers, follow_redirects=True)
    return str(redirect_response.url)


async def fetch_bilibili_transcript(video_url: str) -> Transcript:
    headers = _build_bilibili_headers()

    async with httpx.AsyncClient(timeout=15) as client:
        resolved_url = await _resolve_bilibili_url(client, video_url, headers)
        bvid = extract_bilibili_bvid(resolved_url)
        page = extract_bilibili_page(resolved_url)

        if not bvid:
            raise SubtitleUnavailableError("无法识别 B 站视频编号")

        cached = load_bilibili_transcript(bvid, page)
        if cached:
            return cached

        view_response = await client.get(
            "https://api.bilibili.com/x/web-interface/view",
            params={"bvid": bvid},
            headers=headers,
        )
        view_payload = view_response.json()
        cid = _pick_bilibili_cid(view_payload, page)
        if view_payload.get("code") != 0 or not cid:
            raise SubtitleUnavailableError("未能读取 B 站视频信息")

        player_response = await client.get(
            "https://api.bilibili.com/x/player/wbi/v2",
            params={"bvid": bvid, "cid": cid},
            headers=headers,
        )
        player_payload = player_response.json()
        tracks = player_payload.get("data", {}).get("subtitle", {}).get("subtitles", []) or []
        track = _pick_bilibili_track(tracks)
        subtitle_url = track.get("subtitle_url") if track else None
        if player_payload.get("code") != 0 or not subtitle_url:
            raise SubtitleUnavailableError("当前 B 站视频没有可直接读取的字幕")

        normalized_url = f"https:{subtitle_url}" if str(subtitle_url).startswith("//") else subtitle_url
        subtitle_response = await client.get(normalized_url, headers=headers)
        body = subtitle_response.json().get("body") or []

    segments = [
        TranscriptSegment(
            start=float(item.get("from", 0)),
            end=float(item.get("to", 0)),
            text=str(item.get("content") or "").strip(),
        )
        for item in body
        if str(item.get("content") or "").strip()
    ]

    if not segments:
        raise SubtitleUnavailableError("当前 B 站视频字幕内容为空")

    return Transcript(
        language=str(track.get("lan") or "zh"),
        full_text=" ".join(segment.text for segment in segments),
        segments=segments,
    )


def _build_youtube_api() -> YouTubeTranscriptApi:
    proxy = get_effective_proxy_url()
    if not proxy:
        return YouTubeTranscriptApi()

    session = requests.Session()
    session.proxies = {
        "http": proxy,
        "https": proxy,
    }
    return YouTubeTranscriptApi(http_client=session)


def fetch_youtube_transcript(video_url: str) -> Transcript:
    video_id = extract_youtube_video_id(video_url)
    if not video_id:
        raise SubtitleUnavailableError("无法识别 YouTube 视频编号")

    try:
        transcript_list = _build_youtube_api().list(video_id)
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        if "Too Many Requests" in message or "blocking requests from your IP" in message:
            raise SubtitleBlockedError("YouTube 暂时阻止了字幕请求，请稍后重试") from exc
        raise SubtitleUnavailableError("当前 YouTube 视频没有可直接读取的字幕") from exc

    preferred_languages = ["zh-Hans", "zh", "zh-CN", "zh-TW", "en", "en-US", "ja"]
    transcript_track = None

    try:
        transcript_track = transcript_list.find_manually_created_transcript(preferred_languages)
    except Exception:  # noqa: BLE001
        try:
            transcript_track = transcript_list.find_generated_transcript(preferred_languages)
        except Exception:  # noqa: BLE001
            transcript_track = next(iter(transcript_list), None)

    if transcript_track is None:
        raise SubtitleUnavailableError("当前 YouTube 视频没有可直接读取的字幕")

    try:
        snippets = transcript_track.fetch()
    except Exception as exc:  # noqa: BLE001
        raise SubtitleUnavailableError("读取 YouTube 字幕失败") from exc

    segments: list[TranscriptSegment] = []
    for snippet in snippets:
        if isinstance(snippet, dict):
            text = str(snippet.get("text") or "").strip()
            start = float(snippet.get("start", 0))
            duration = float(snippet.get("duration", 0))
        else:
            text = str(getattr(snippet, "text", "") or "").strip()
            start = float(getattr(snippet, "start", 0))
            duration = float(getattr(snippet, "duration", 0))

        if not text:
            continue

        segments.append(
            TranscriptSegment(
                start=start,
                end=start + duration,
                text=text,
            )
        )

    if not segments:
        raise SubtitleUnavailableError("当前 YouTube 视频字幕内容为空")

    return Transcript(
        language=str(getattr(transcript_track, "language_code", "unknown")),
        full_text=" ".join(segment.text for segment in segments),
        segments=segments,
    )
