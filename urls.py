"""core/urls.py — YouTube URL extraction and formatting helpers."""

import re

_YT_URL_RE = re.compile(
    r"(?:https?://)?"
    r"(?:www\.|m\.)?"
    r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{6,})"
)


def extract_youtube_urls(text: str) -> list:
    """Return a de-duplicated list of canonical YouTube watch URLs, in order."""
    seen = set()
    out = []
    for m in _YT_URL_RE.finditer(text or ""):
        vid = m.group(1)
        url = f"https://www.youtube.com/watch?v={vid}"
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def format_single(text: str) -> str:
    """Return the first URL found in `text`, or `text.strip()` if none."""
    urls = extract_youtube_urls(text)
    return urls[0] if urls else (text or "").strip()