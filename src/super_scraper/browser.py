"""Optional Chromium renderer; no persistent profile, login, or OG reconstruction."""

import base64
import time
from collections.abc import Callable

from .http import USER_AGENT, HttpFetcher, _retry_delay, require_html
from .models import DependencyError, FetchedPage, Options, ScrapeError


class BrowserFetcher:
    def __init__(self, options: Options, http: HttpFetcher):
        self.options = options
        self.http = http
        self._playwright = None
        self._browser = None

    def __enter__(self):
        try:
            from playwright.sync_api import Error, sync_playwright
        except ImportError as exc:
            raise DependencyError(
                "browser_unavailable",
                '請先執行 uv sync --extra browser，或 pip install -e ".[browser]"；'
                "再執行 python -m playwright install chromium",
            ) from exc
        self._error_type = Error
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        except Error as exc:
            self.__exit__()
            raise DependencyError(
                "browser_unavailable",
                "Chromium 無法啟動，請執行 python -m playwright install chromium；" + str(exc),
            ) from exc
        return self

    def __exit__(self, *_):
        try:
            if self._browser:
                self._browser.close()
        finally:
            if self._playwright:
                self._playwright.stop()
        self._browser = None
        self._playwright = None

    def _read_document(self, session, event, url: str) -> bytes:
        """Read the decoded main response as a bounded CDP stream before rendering."""
        stream = session.send("Fetch.takeResponseBodyAsStream", {"requestId": event["requestId"]})[
            "stream"
        ]
        chunks: list[bytes] = []
        size = 0
        deadline = time.monotonic() + self.options.timeout
        try:
            while True:
                chunk = session.send(
                    "IO.read",
                    {
                        "handle": stream,
                        "size": min(65536, self.options.max_bytes - size + 1),
                    },
                )
                data = (
                    base64.b64decode(chunk["data"])
                    if chunk.get("base64Encoded")
                    else chunk["data"].encode("utf-8")
                )
                size += len(data)
                if size > self.options.max_bytes:
                    raise ScrapeError("response_too_large", "主要文件超過大小限制", final_url=url)
                if time.monotonic() > deadline:
                    raise ScrapeError("network_error", "主要文件傳輸逾時", final_url=url)
                chunks.append(data)
                if chunk["eof"]:
                    return b"".join(chunks)
        finally:
            session.send("IO.close", {"handle": stream})

    def _fetch_once(self, url: str, before_request: Callable | None) -> FetchedPage:
        if self._browser is None:
            raise RuntimeError("BrowserFetcher must be used as a context manager")
        context = self._browser.new_context(
            user_agent=USER_AGENT,
            service_workers="block",
            accept_downloads=False,
        )
        page = context.new_page()
        errors: list[ScrapeError] = []
        session = None
        closing = False
        on_paused = None
        try:
            # CDP intercepts every top-level navigation, including HTTP redirects.
            # Playwright route callbacks alone do not intercept every redirect hop.
            session = context.new_cdp_session(page)
            main_frame_id = session.send("Page.getFrameTree")["frameTree"]["frame"]["id"]

            def handle_paused(event):
                request_id = event["requestId"]
                current_url = event["request"]["url"]
                is_main = event.get("frameId") == main_frame_id
                response_stage = "responseStatusCode" in event or "responseErrorReason" in event
                try:
                    if is_main and response_stage:
                        status = event.get("responseStatusCode", 0)
                        headers = {
                            entry["name"].lower(): entry["value"]
                            for entry in event.get("responseHeaders", [])
                        }
                        if status >= 400:
                            raise ScrapeError(
                                f"http_{status}", f"伺服器回應 HTTP {status}", final_url=current_url
                            )
                        if 200 <= status < 300:
                            require_html(headers.get("content-type", ""), current_url)
                            length = headers.get("content-length", "")
                            if length.isdigit() and int(length) > self.options.max_bytes:
                                raise ScrapeError(
                                    "response_too_large", "文件超過大小限制", final_url=current_url
                                )
                            body = self._read_document(session, event, current_url)
                            # CDP streams decoded bytes. Preserve original metadata headers,
                            # but remove wire-encoding/length headers before fulfilling.
                            response_headers = [
                                entry
                                for entry in event.get("responseHeaders", [])
                                if entry["name"].lower()
                                not in {
                                    "content-encoding",
                                    "content-length",
                                    "transfer-encoding",
                                }
                            ]
                            session.send(
                                "Fetch.fulfillRequest",
                                {
                                    "requestId": request_id,
                                    "responseCode": status,
                                    "responseHeaders": response_headers,
                                    "body": base64.b64encode(body).decode("ascii"),
                                },
                            )
                            return
                    elif is_main and before_request:
                        before_request(current_url)
                    method = "Fetch.continueResponse" if response_stage else "Fetch.continueRequest"
                    params = {"requestId": request_id}
                    if not response_stage:
                        params["interceptResponse"] = True
                    session.send(method, params)
                except ScrapeError as exc:
                    errors.append(exc)
                    session.send(
                        "Fetch.failRequest", {"requestId": request_id, "errorReason": "Aborted"}
                    )

            def on_paused(event):
                try:
                    handle_paused(event)
                except self._error_type as exc:
                    # Late iframe events may finish after context teardown. Real
                    # interception failures are retained as per-article errors.
                    if not closing and event.get("frameId") == main_frame_id:
                        errors.append(ScrapeError("network_error", str(exc), final_url=url))

            session.on("Fetch.requestPaused", on_paused)
            session.send(
                "Fetch.enable",
                {"patterns": [{"resourceType": "Document", "requestStage": "Request"}]},
            )
            response = page.goto(
                url, wait_until="domcontentloaded", timeout=self.options.timeout * 1000
            )
            if errors:
                raise errors[0]
            if response is None:
                raise ScrapeError("no_response", "瀏覽器沒有取得主要文件", final_url=page.url)
            require_html(response.headers.get("content-type", ""), page.url)
            if self.options.wait_ms:
                page.wait_for_timeout(self.options.wait_ms)
            if errors:
                raise errors[0]
            html = page.content()
            if errors:
                raise errors[0]
            if len(html.encode("utf-8")) > self.options.max_bytes:
                raise ScrapeError(
                    "response_too_large", "渲染後 HTML 超過大小限制", final_url=page.url
                )
            return FetchedPage(html=html, final_url=page.url, status_code=response.status)
        except self._error_type as exc:
            if errors:
                raise errors[0] from exc
            raise ScrapeError("network_error", str(exc), final_url=url) from exc
        finally:
            closing = True
            if session is not None and on_paused is not None:
                session.remove_listener("Fetch.requestPaused", on_paused)
            context.close()

    def fetch(self, url: str, before_request: Callable | None = None) -> FetchedPage:
        for attempt in range(self.options.retries + 1):
            try:
                return self._fetch_once(url, before_request)
            except ScrapeError as exc:
                retryable = exc.code in {
                    "network_error",
                    "http_429",
                    "http_500",
                    "http_502",
                    "http_503",
                    "http_504",
                }
                if not retryable or attempt == self.options.retries:
                    raise
                time.sleep(_retry_delay(attempt, {}))
        raise AssertionError("unreachable retry loop")
