"""Run the same fetch/extract components as the CLI, retaining diagnostic HTML.

Errors and access restrictions are expected benchmark observations. Completing
a run is not a quality pass; use verify_extended_sites.py to audit article copy.
All full-page HTML and article exports stay in ignored local directories.
"""

import argparse
import json
import time
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path

from super_scraper.browser import BrowserFetcher
from super_scraper.export import export_results
from super_scraper.extractor import extract_article
from super_scraper.http import HttpFetcher
from super_scraper.inputs import normalize_url
from super_scraper.models import Options, ScrapeError, ScrapeResult
from super_scraper.robots import RobotsPolicy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["http", "browser"], required=True)
    parser.add_argument("--phase", default="final")
    parser.add_argument("--manifest", type=Path, default=Path("examples/extended-sites.json"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/extended-sites"))
    parser.add_argument("--output", type=Path, default=Path("output/extended-sites"))
    args = parser.parse_args()
    samples = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    options = Options(mode=args.mode, timeout=15, retries=0, wait_ms=2000)
    cache = args.cache / args.phase / args.mode
    cache.mkdir(parents=True, exist_ok=True)
    results = []
    with ExitStack() as stack:
        http = stack.enter_context(HttpFetcher(options))
        fetcher = (
            stack.enter_context(BrowserFetcher(options, http)) if args.mode == "browser" else http
        )
        policy = RobotsPolicy(http)
        for index, sample in enumerate(samples):
            if index:
                time.sleep(options.delay)
            result = ScrapeResult(url=sample["url"], mode=args.mode)

            def check(url, result=result):
                for warning in policy.check(url):
                    if warning not in result.warnings:
                        result.warnings.append(warning)

            try:
                url = normalize_url(sample["url"])
                page = fetcher.fetch(url, before_request=check)
                result.final_url = page.final_url
                # IDs in the checked-in manifest select local snapshot names.
                identifier = sample["id"]
                if not identifier or any(
                    c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in identifier
                ):
                    raise ValueError("Invalid benchmark sample ID")
                data = page.html if isinstance(page.html, bytes) else page.html.encode("utf-8")
                (cache / f"{identifier}.html").write_bytes(data)
                values = asdict(extract_article(page.html, page.final_url))
                warnings = values.pop("warnings")
                for name, value in values.items():
                    setattr(result, name, value)
                result.warnings.extend(warnings)
                if args.mode == "http" and "short_content" in warnings:
                    result.warnings.append("try_browser_mode")
                result.status = "success"
            except ScrapeError as exc:
                result.error = str(exc)
                result.final_url = exc.final_url or result.final_url
            except Exception as exc:
                result.error = f"{type(exc).__name__}: {exc}"
            results.append(result)
            print(
                sample["id"],
                result.status,
                result.char_count,
                result.warnings,
                result.error or "",
                flush=True,
            )
    folder = export_results(results, args.output / args.phase / args.mode)
    (cache / "export.txt").write_text(str(folder), encoding="utf-8")
    print(f"EXPORT {folder}")


if __name__ == "__main__":
    main()
