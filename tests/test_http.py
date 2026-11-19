import pytest

from super_scraper.http import HttpFetcher
from super_scraper.models import Options, ScrapeError
from super_scraper.robots import RobotsPolicy


def test_redirect_returns_final_url_and_bytes(web_server):
    web_server.add("/start", status=302, Location="/article")
    web_server.add("/article", "<article><p>完整文章</p></article>")
    with HttpFetcher(Options(delay=0)) as fetcher:
        page = fetcher.fetch(web_server.base + "/start")
    assert page.final_url == web_server.base + "/article"
    assert "完整文章" in page.html.decode()


def test_redirect_target_robots_denial_prevents_article_download(web_server):
    web_server.add("/robots.txt", "User-agent: *\nDisallow: /private\n", content_type="text/plain")
    web_server.add("/start", status=302, Location="/private")
    web_server.add("/private", "secret")
    with HttpFetcher(Options(delay=0)) as fetcher:
        policy = RobotsPolicy(fetcher)
        with pytest.raises(ScrapeError, match="robots_disallowed"):
            fetcher.fetch(web_server.base + "/start", before_request=policy.check)
    assert web_server.hits["/private"] == 0
    assert web_server.hits["/robots.txt"] == 1


@pytest.mark.parametrize("status", [429, 503])
def test_transient_errors_retry_then_succeed(web_server, status):
    web_server.routes["/retry"] = lambda hit: (
        (status, {"Retry-After": "0", "Content-Type": "text/html"}, "busy")
        if hit < 3
        else (200, {"Content-Type": "text/html"}, "<article>Recovered</article>")
    )
    with HttpFetcher(Options(delay=0)) as fetcher:
        page = fetcher.fetch(web_server.base + "/retry")
    assert b"Recovered" in page.html
    assert web_server.hits["/retry"] == 3


def test_transient_retry_exhaustion_is_bounded(web_server):
    web_server.add("/busy", "busy", status=503, **{"Retry-After": "0"})
    with HttpFetcher(Options(delay=0, retries=2)) as fetcher:
        with pytest.raises(ScrapeError, match="http_503"):
            fetcher.fetch(web_server.base + "/busy")
    assert web_server.hits["/busy"] == 3


def test_permanent_failure_is_not_retried(web_server):
    with HttpFetcher(Options(delay=0)) as fetcher:
        with pytest.raises(ScrapeError, match="http_404"):
            fetcher.fetch(web_server.base + "/missing")
    assert web_server.hits["/missing"] == 1


@pytest.mark.parametrize(
    "content_type,body,code",
    [
        ("application/pdf", b"%PDF", "non_html"),
        ("text/html", b"x" * 1025, "response_too_large"),
    ],
)
def test_non_html_and_oversize_are_rejected(web_server, content_type, body, code):
    web_server.add("/bad", body, content_type=content_type)
    with HttpFetcher(Options(delay=0, max_bytes=1024)) as fetcher:
        with pytest.raises(ScrapeError, match=code):
            fetcher.fetch(web_server.base + "/bad")


def test_robots_missing_warns_and_is_cached(web_server):
    web_server.add("/robots.txt", status=404)
    with HttpFetcher(Options(delay=0)) as fetcher:
        policy = RobotsPolicy(fetcher)
        assert policy.check(web_server.base + "/article") == ["robots_unavailable"]
        assert policy.check(web_server.base + "/other") == ["robots_unavailable"]
    assert web_server.hits["/robots.txt"] == 1


def test_redirect_loop_is_bounded(web_server):
    web_server.add("/loop", status=302, Location="/loop")
    with HttpFetcher(Options(delay=0)) as fetcher:
        with pytest.raises(ScrapeError, match="too_many_redirects"):
            fetcher.fetch(web_server.base + "/loop")
    assert web_server.hits["/loop"] <= 11
