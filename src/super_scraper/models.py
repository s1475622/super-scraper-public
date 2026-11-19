"""Shared data contracts for extraction, fetching and export."""

import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime


class ScrapeError(Exception):
    def __init__(self, code: str, message: str, *, final_url: str | None = None):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.final_url = final_url


class DependencyError(ScrapeError):
    """A missing optional runtime is a global configuration error."""


@dataclass(frozen=True)
class Options:
    mode: str = "http"
    timeout: float = 20
    delay: float = 1
    retries: int = 2
    max_bytes: int = 10 * 1024 * 1024
    wait_ms: int = 2000

    def __post_init__(self):
        if self.mode not in {"http", "browser"}:
            raise ValueError("mode 必須是 http 或 browser")
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("timeout 必須是有限正數")
        if not math.isfinite(self.delay) or self.delay < 0:
            raise ValueError("delay 必須是有限非負數")
        if not 0 <= self.retries <= 5:
            raise ValueError("retries 必須介於 0 與 5")
        if self.max_bytes <= 0:
            raise ValueError("max_bytes 必須是正數")
        if not 0 <= self.wait_ms <= 10000:
            raise ValueError("wait_ms 必須介於 0 與 10000")


@dataclass
class FetchedPage:
    html: bytes | str
    final_url: str
    status_code: int


@dataclass
class Article:
    text: str
    markdown: str
    title: str | None = None
    author: str | None = None
    published_date: str | None = None
    site_name: str | None = None
    language: str | None = None
    canonical_url: str | None = None
    char_count: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class ScrapeResult:
    url: str
    mode: str
    status: str = "error"
    final_url: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    author: str | None = None
    published_date: str | None = None
    site_name: str | None = None
    language: str | None = None
    text: str = ""
    markdown: str = ""
    char_count: int = 0
    extracted_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)
