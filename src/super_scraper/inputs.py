"""Read supplied URLs; never discover or recursively crawl links."""

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def normalize_url(value: str) -> str:
    value = value.strip()
    if any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("網址含有空白或控制字元")
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            raise ValueError("僅支援完整的 HTTP(S) 網址")
        if parts.username is not None or parts.password is not None:
            raise ValueError("不支援含帳號密碼的網址")
        if parts.port is not None and not 1 <= parts.port <= 65535:
            raise ValueError("連接埠無效")
    except ValueError as exc:
        raise ValueError(f"無效網址 {value!r}: {exc}") from exc
    return urlunsplit((parts.scheme.lower(), parts.netloc, parts.path, parts.query, ""))


def collect_urls(urls: list[str], file: Path | None = None) -> list[str]:
    entries = list(urls)
    if file is not None:
        entries.extend(file.read_text(encoding="utf-8-sig").splitlines())
    result: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        entry = entry.strip()
        if not entry or entry.startswith("#"):
            continue
        try:
            entry = normalize_url(entry)
        except ValueError:
            # Preserve bad individual input so the exported record explains it.
            pass
        if entry not in seen:
            result.append(entry)
            seen.add(entry)
    if not result:
        raise ValueError("請提供至少一個文章網址，或使用 --file urls.txt")
    return result
