"""Read URL lists. One URL per line; blanks and # comments skipped. No crawl."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


class UrlReadError(ValueError):
    pass


def normalize_url(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return text
    return None


def read_urls_file(path: str | Path) -> list[str]:
    p = Path(path)
    if not p.is_file():
        raise UrlReadError(f"urls file not found: {p}")
    try:
        text = p.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise UrlReadError(f"cannot read urls file: {exc}") from exc
    return parse_url_lines(text)


def parse_url_lines(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped not in seen:
            seen.add(stripped)
            urls.append(stripped)
    return urls


def collect_urls(*, file: str | None, args: list[str] | None) -> list[str]:
    urls: list[str] = []
    if file:
        urls.extend(read_urls_file(file))
    if args:
        for item in args:
            if item and item not in urls:
                urls.append(item)
    return urls
