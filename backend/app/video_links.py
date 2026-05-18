from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


BILIBILI_BVID_PATTERN = re.compile(r"BV[0-9A-Za-z]+")


def extract_bilibili_bvid(video_url: str) -> str | None:
    match = BILIBILI_BVID_PATTERN.search(video_url)
    return match.group(0) if match else None


def extract_bilibili_page(video_url: str) -> int:
    page = parse_qs(urlparse(video_url).query).get("p", ["1"])[0]
    try:
        parsed_page = int(page)
    except (TypeError, ValueError):
        return 1
    return max(parsed_page, 1)


def extract_youtube_video_id(video_url: str) -> str | None:
    parsed = urlparse(video_url)
    host = parsed.netloc.lower()

    if host.endswith("youtu.be"):
        return parsed.path.lstrip("/") or None

    if "youtube.com" not in host:
        return None

    query_video_id = parse_qs(parsed.query).get("v", [None])[0]
    if query_video_id:
        return query_video_id

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts", "live"}:
        return path_parts[1]

    return None
