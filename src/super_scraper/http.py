"""Bounded streaming HTTP downloads, with policy checks on every redirect."""

import time
from collections.abc import Callable
from email.message import Message
from urllib.parse import urljoin

import httpx

from .inputs import normalize_url
from .models import FetchedPage, Options, ScrapeError

USER_AGENT = "SuperScraper/0.1"
_REDIRECTS = {301, 302, 303, 307, 308}
_RETRYABLE = {429, 500, 502, 503, 504}


def require_html(content_type: str, url: str):
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type and media_type not in {"text/html", "application/xhtml+xml"}:
        raise ScrapeError("non_html", f"非 HTML 文件：{media_type}", final_url=url)


def _retry_delay(attempt: int, headers: dict[str, str]) -> float:
    try:
        delay = float(headers.get("retry-after", ""))
        if delay >= 0:
            return min(delay, 5)
    except ValueError:
        pass
    return min(0.5 * (2**attempt), 5)


class HttpFetcher:
    def __init__(self, options: Options):
        self.options = options
        self.client = httpx.Client(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.1",
            },
            timeout=options.timeout,
            follow_redirects=False,
        )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.client.close()

    def _request(self, url: str, html_only: bool) -> tuple[int, dict[str, str], bytes]:
        for attempt in range(self.options.retries + 1):
            headers: dict[str, str] = {}
            try:
                deadline = time.monotonic() + self.options.timeout
                with self.client.stream("GET", url) as response:
                    status = response.status_code
                    headers = dict(response.headers)
                    if status in _REDIRECTS:
                        return status, headers, b""
                    if status >= 400:
                        raise ScrapeError(
                            f"http_{status}", f"伺服器回應 HTTP {status}", final_url=url
                        )
                    if html_only:
                        require_html(headers.get("content-type", ""), url)
                    length = headers.get("content-length", "")
                    if length.isdigit() and int(length) > self.options.max_bytes:
                        raise ScrapeError("response_too_large", "文件超過大小限制", final_url=url)
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > self.options.max_bytes:
                            raise ScrapeError(
                                "response_too_large", "文件超過大小限制", final_url=url
                            )
                        if time.monotonic() > deadline:
                            raise httpx.ReadTimeout("document transfer exceeded timeout")
                        chunks.append(chunk)
                    return status, headers, b"".join(chunks)
            except ScrapeError as exc:
                if exc.code not in {f"http_{status}" for status in _RETRYABLE}:
                    raise
                if attempt == self.options.retries:
                    raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                if attempt == self.options.retries:
                    raise ScrapeError("network_error", str(exc), final_url=url) from exc
            time.sleep(_retry_delay(attempt, headers))
        raise AssertionError("unreachable retry loop")

    def fetch(
        self,
        url: str,
        before_request: Callable[[str], object] | None = None,
        *,
        html_only: bool = True,
    ) -> FetchedPage:
        current = url
        for _ in range(11):
            try:
                current = normalize_url(current)
            except ValueError as exc:
                raise ScrapeError("invalid_url", str(exc), final_url=current) from exc
            if before_request:
                before_request(current)
            status, headers, body = self._request(current, html_only)
            if status in _REDIRECTS:
                target = headers.get("location")
                if not target:
                    raise ScrapeError(
                        "invalid_redirect", "重新導向缺少 Location", final_url=current
                    )
                current = urljoin(current, target)
                continue
            if html_only and not headers.get("content-type"):
                prefix = body.lstrip(b"\xef\xbb\xbf \r\n\t").lower()
                if not prefix.startswith((b"<!doctype html", b"<html", b"<article", b"<main")):
                    raise ScrapeError("non_html", "無法確認文件為 HTML", final_url=current)
            html: bytes | str = body
            # Honor an explicitly declared legacy encoding even if HTML lacks a meta charset.
            message = Message()
            message["content-type"] = headers.get("content-type", "")
            charset = message.get_content_charset()
            if html_only and charset and charset.lower() not in {"utf-8", "utf8"}:
                try:
                    html = body.decode(charset)
                except (LookupError, UnicodeError):
                    pass  # Extraction library can still inspect meta charset or detect encoding.
            return FetchedPage(html=html, final_url=current, status_code=status)
        raise ScrapeError("too_many_redirects", "重新導向超過 10 次", final_url=current)
