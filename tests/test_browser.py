import gzip
import sys
from types import SimpleNamespace

import pytest

from super_scraper.browser import BrowserFetcher
from super_scraper.http import HttpFetcher
from super_scraper.models import DependencyError, Options, ScrapeError
from super_scraper.pipeline import run_batch
from super_scraper.robots import RobotsPolicy


@pytest.mark.parametrize("during_navigation", [False, True, "main_content"])
def test_late_subframe_callback_during_context_close_does_not_escape(during_navigation):
    """A detached ad frame must not turn a completed article into an exception."""

    class ClosedError(Exception):
        pass

    listeners = {}
    closed = False
    fail_callback = False

    def send(method, params=None):
        if closed or (fail_callback and method == "Fetch.continueRequest"):
            raise ClosedError("Target page, context or browser has been closed")
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "main"}}}
        return {}

    session = SimpleNamespace(
        send=send,
        on=lambda event, callback: listeners.update({event: callback}),
        remove_listener=lambda event, callback: listeners.pop(event, None),
    )

    def close():
        nonlocal closed
        closed = True
        callback = listeners.get("Fetch.requestPaused")
        if callback:
            callback(
                {
                    "requestId": "late",
                    "frameId": "advert",
                    "request": {"url": "https://example.com/ad"},
                }
            )

    def goto(*args, **kwargs):
        nonlocal fail_callback
        if during_navigation is True:
            fail_callback = True
            listeners["Fetch.requestPaused"](
                {
                    "requestId": "late",
                    "frameId": "advert",
                    "request": {"url": "https://example.com/ad"},
                }
            )
            fail_callback = False
        return SimpleNamespace(headers={"content-type": "text/html"}, status=200)

    def content():
        nonlocal fail_callback
        if during_navigation == "main_content":
            fail_callback = True
            listeners["Fetch.requestPaused"](
                {
                    "requestId": "changed",
                    "frameId": "main",
                    "request": {"url": "https://example.com/article"},
                }
            )
            fail_callback = False
        return "<article><p>A completed article.</p></article>"

    page = SimpleNamespace(
        goto=goto,
        url="https://example.com/article",
        content=content,
    )
    context = SimpleNamespace(
        new_page=lambda: page, new_cdp_session=lambda page: session, close=close
    )
    options = Options(mode="browser", wait_ms=0)
    with HttpFetcher(options) as http:
        fetcher = BrowserFetcher(options, http)
        fetcher._browser = SimpleNamespace(new_context=lambda **kwargs: context)
        fetcher._error_type = ClosedError
        if during_navigation == "main_content":
            with pytest.raises(ScrapeError, match="network_error"):
                fetcher._fetch_once(page.url, None)
            assert closed
            return
        result = fetcher._fetch_once(page.url, None)
    assert "A completed article." in result.html
    assert closed


def test_missing_optional_browser_dependency_has_install_instructions(monkeypatch):
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    with HttpFetcher(Options(mode="browser")) as http:
        with pytest.raises(DependencyError, match="browser"):
            with BrowserFetcher(Options(mode="browser"), http):
                pass


@pytest.mark.browser
def test_javascript_article_renders_and_is_extracted(web_server):
    web_server.add(
        "/dynamic",
        """<html lang="zh-Hant"><head><meta charset="utf-8">
    <title>動態文章</title></head><body><div id="root"></div><script>
    setTimeout(() => document.querySelector('#root').innerHTML =
    '<article><h1>動態文章標題</h1><p>這段正文是執行 JavaScript 後才出現的內容。</p></article>', 100);
    </script></body></html>""",
    )
    results = run_batch(
        [web_server.base + "/dynamic"], Options(mode="browser", delay=0, wait_ms=500)
    )
    assert results[0].status == "success", results[0].error
    assert "這段正文是執行 JavaScript 後才出現的內容。" in results[0].text


@pytest.mark.browser
def test_browser_checks_robots_before_redirected_document(web_server):
    web_server.add("/robots.txt", "User-agent: *\nDisallow: /private", content_type="text/plain")
    web_server.add("/start", status=302, Location="/private")
    web_server.add("/private", "<article>Disallowed content</article>")
    options = Options(mode="browser", delay=0, wait_ms=0, retries=0)
    with HttpFetcher(options) as http:
        policy = RobotsPolicy(http)
        with BrowserFetcher(options, http) as browser:
            with pytest.raises(ScrapeError, match="robots_disallowed"):
                browser.fetch(web_server.base + "/start", before_request=policy.check)
    assert web_server.hits["/private"] == 0


@pytest.mark.browser
@pytest.mark.parametrize(
    "path,body,status,content_type,code",
    [
        ("/pdf", b"%PDF", 200, "application/pdf", "non_html"),
        ("/missing", "<p>Not found</p>", 404, "text/html", "http_404"),
        (
            "/large",
            "<html><body>" + "x" * 2048 + "</body></html>",
            200,
            "text/html",
            "response_too_large",
        ),
    ],
)
def test_browser_rejects_invalid_documents(web_server, path, body, status, content_type, code):
    web_server.add(path, body, status=status, content_type=content_type)
    options = Options(mode="browser", delay=0, retries=0, wait_ms=0, max_bytes=1024)
    with HttpFetcher(options) as http:
        with BrowserFetcher(options, http) as browser:
            with pytest.raises(ScrapeError, match=code):
                browser.fetch(web_server.base + path)


@pytest.mark.browser
@pytest.mark.parametrize("compressed", [False, True])
def test_browser_limits_transferred_body_even_if_script_removes_large_dom(web_server, compressed):
    html = (
        '<html><body><div id="large">'
        + "x" * 5000
        + '</div><script>document.getElementById("large").remove()</script>'
        "<article><p>A tiny article remains.</p></article></body></html>"
    ).encode()
    if compressed:
        web_server.add("/huge", gzip.compress(html), **{"Content-Encoding": "gzip"})
    else:
        web_server.add("/huge", html, **{"Content-Length": None})
    options = Options(mode="browser", delay=0, retries=0, wait_ms=0, max_bytes=1024)
    with HttpFetcher(options) as http:
        with BrowserFetcher(options, http) as browser:
            with pytest.raises(ScrapeError, match="response_too_large"):
                browser.fetch(web_server.base + "/huge")
