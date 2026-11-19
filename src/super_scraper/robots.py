"""Cache robots policies by origin; preserve uncertainty as a warning."""

from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from .http import USER_AGENT, HttpFetcher
from .models import ScrapeError


class RobotsPolicy:
    def __init__(self, fetcher: HttpFetcher):
        self.fetcher = fetcher
        self.cache: dict[str, RobotFileParser | None] = {}

    def check(self, url: str) -> list[str]:
        parsed = urlsplit(url)
        origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        if origin not in self.cache:
            robots_url = origin + "/robots.txt"
            try:
                result = self.fetcher.fetch(robots_url, html_only=False)
                content = result.html
                text = (
                    content.decode("utf-8-sig", errors="replace")
                    if isinstance(content, bytes)
                    else content
                )
                if "<html" in text[:500].lower() or "<!doctype" in text[:500].lower():
                    raise ScrapeError("invalid_robots", "robots.txt 回傳了 HTML")
                parser = RobotFileParser(robots_url)
                parser.parse(text.splitlines())
                self.cache[origin] = parser
            except (ScrapeError, httpx.HTTPError):
                self.cache[origin] = None
        parser = self.cache[origin]
        if parser is None:
            return ["robots_unavailable"]
        if not parser.can_fetch(USER_AGENT, url):
            raise ScrapeError("robots_disallowed", "robots.txt 明確禁止此路徑", final_url=url)
        return []
