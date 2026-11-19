"""Sequential batches with per-URL failures isolated into result records."""

import time
from contextlib import ExitStack
from dataclasses import asdict

from .browser import BrowserFetcher
from .extractor import extract_article
from .http import HttpFetcher
from .inputs import normalize_url
from .models import Options, ScrapeError, ScrapeResult
from .robots import RobotsPolicy


def run_batch(urls: list[str], options: Options, progress=None) -> list[ScrapeResult]:
    results: list[ScrapeResult] = []
    with ExitStack() as stack:
        http = stack.enter_context(HttpFetcher(options))
        fetcher = (
            stack.enter_context(BrowserFetcher(options, http))
            if options.mode == "browser"
            else http
        )
        policy = RobotsPolicy(http)
        for index, supplied_url in enumerate(urls):
            if index and options.delay:
                time.sleep(options.delay)
            result = ScrapeResult(url=supplied_url, mode=options.mode)

            def before_request(target, result=result):
                for warning in policy.check(target):
                    if warning not in result.warnings:
                        result.warnings.append(warning)

            try:
                normalized = normalize_url(supplied_url)
                page = fetcher.fetch(normalized, before_request=before_request)
                result.final_url = page.final_url
                article = extract_article(page.html, page.final_url)
                values = asdict(article)
                warnings = values.pop("warnings")
                for name, value in values.items():
                    setattr(result, name, value)
                result.warnings.extend(warnings)
                if options.mode == "http" and "short_content" in warnings:
                    result.warnings.append("try_browser_mode")
                result.status = "success"
            except ValueError as exc:
                result.error = f"invalid_url: {exc}"
            except ScrapeError as exc:
                result.error = str(exc)
                result.final_url = exc.final_url or result.final_url
            except Exception as exc:
                result.error = f"unexpected_error: {type(exc).__name__}: {exc}"
            results.append(result)
            if progress:
                progress(index + 1, len(urls), result)
    return results
