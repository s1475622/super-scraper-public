# Article Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deliver a local CLI that extracts supplied article URLs in batches and exports auditable text and metadata.

**Architecture:** Combine Trafilatura extraction with BeautifulSoup/markdownify fallback. Separate pure extraction, bounded fetching and robots policy, and batch/export/CLI orchestration. HTTP is default; Playwright is optional and explicit.

**Tech Stack:** Python >=3.11 (local 3.13), Trafilatura 2.x, BeautifulSoup4, markdownify, HTTPX, optional Playwright, pytest, Ruff, uv lockfile.

**Spec:** docs/superpowers/specs/2026-11-19-article-scraper-design.md

## Global Constraints

- Input is one or more supplied HTTP(S) URLs or a UTF-8 file, not site discovery.
- Default: sequential fetching, one second between URLs, 20-second network timeout, at most two extra transient retries, 10 MiB HTML limit.
- JSON/UTF-8 BOM CSV include successes and failures; per-article UTF-8 TXT and Markdown contain actual extracted content.
- Unique output directory per run, no overwriting previous exports; preserve query strings and remove fragments for deduplication.
- Missing metadata is null, character counts exclude whitespace, under 100 characters warns, empty body fails.
- Explicit robots disallow is respected; unavailable robots is recorded as a warning. Browser has no user profile or automatic login.
- CLI exit codes: 0 success including warnings, 1 partial/individual failure, 2 invalid global input/configuration/dependency/output.

## Review Focus

- Redirect to a robots-disallowed URL must not download the disallowed article.
- HTTP-200 verification/login pages must not silently look like trustworthy complete articles.
- Chinese character counts, legacy HTML encoding, missing dates/authors must remain honest.
- Retrying, redirect loops, huge/non-HTML pages must stay bounded and not abort a batch.
- Optional browser dependency failure must be actionable, and its processes/context must close.

## Files and responsibilities

- `src/super_scraper/models.py`: options, result records, typed errors.
- `inputs.py`: URL/file validation and ordered deduplication.
- `extractor.py`: pure HTML-to-text/Markdown/metadata extraction and quality flags.
- `http.py`: bounded HTML downloads, manual redirects, retry behavior.
- `robots.py`: cached policy checks and warnings, including redirected targets.
- `browser.py`: lazy Playwright import, rendered document retrieval and clean resource ownership.
- `pipeline.py`: ordered batch and failure isolation.
- `export.py`: JSON/CSV/TXT/Markdown writing in unique run directories.
- `cli.py`, `__main__.py`: argparse and exit codes.
- `tests/`: local HTML and HTTP fixtures; real CLI subprocess and optional browser integration.
- `README.md`, `examples/urls.txt`, `pyproject.toml`, `uv.lock`: usable installation, invocation and provenance.

### Task 1: Extract actual article content

**Interfaces:** `extract_article(html: str | bytes, url: str) -> Article`; `Article` carries text, markdown, metadata and quality warnings. `ScrapeResult` adds source/final URL, status, timestamp and error.

- [x] Write `tests/test_extractor.py`: Chinese paragraphs preserved, menus/comments excluded, title/author/date available, missing metadata null, empty fails, short actual body warns, OG-only page is not expanded to full text, suspected login wall warns.
- [x] Run `.venv/Scripts/python -m pytest tests/test_extractor.py -q`; expect missing extraction implementation.
- [x] Implement models and extractor using Trafilatura; limited semantic-container fallback with explicit warning, no OG reconstruction.
- [x] Run the same test file; expect all pass.

### Task 2: Validate and download safely in bounded time

**Interfaces:** `collect_urls(urls: list[str], file: Path | None) -> list[str]`; `HttpFetcher.fetch(url: str, before_request: Callable | None = None) -> FetchedPage`; `RobotsPolicy.check(url: str) -> list[str]` raises `ScrapeError` on explicit denial.

- [x] Write input tests for BOM/comments/fragment dedup/query preservation and bad schemes/ports; use a local HTTP server to test redirects, robots denial at redirect targets, 429/503 retry counts, permanent 404, content type/size, encoding and missing robots warning.
- [x] Run `.venv/Scripts/python -m pytest tests/test_inputs.py tests/test_http.py -q`; expect missing implementations.
- [x] Implement inputs, HTTP transport and cached robots policy. Manually validate each redirect; cap redirect count at 10 and retry backoff/Retry-After at 5 seconds.
- [x] Run both test files; expect all pass.

### Task 3: Batch CLI, exports and browser mode

**Interfaces:** `run_batch(urls: list[str], options: Options) -> list[ScrapeResult]`; `export_results(results: list[ScrapeResult], base: Path) -> Path`; `main(argv: list[str] | None = None) -> int`; `BrowserFetcher.fetch(url: str, before_request: Callable | None = None) -> FetchedPage`.

- [x] Write CLI integration tests via actual subprocess against local HTTP fixtures: success/404/success isolation, JSON and CSV values, UTF-8 BOM, safe TXT paths, separate output directories, invalid options before network and missing dependencies. Write an opt-in browser test for delayed JS injection, non-HTML and error pages.
- [x] Run `.venv/Scripts/python -m pytest tests/test_cli.py tests/test_browser.py -q`; expect missing CLI/browser behavior.
- [x] Implement browser reuse with a fresh context per URL, bounded waits and top-level redirect robots checks. Implement sequential batch, artifacts and CLI; add console script and module invocation.
- [x] Run CLI tests and then browser tests with `--run-browser`; expect all pass after Chromium installation.

### Task 4: Delivery and whole-project verification

- [x] Write Traditional Chinese README covering install, single/multiple/file URLs, browser installation/mode, output schema/warnings, exit codes, limitations, tests, and source provenance. Include Windows launch helper and examples.
- [x] Run `.venv/Scripts/python -m pytest --run-browser -q`, `.venv/Scripts/python -m ruff check .`, `.venv/Scripts/python -m super_scraper --help`, and a real public article smoke run. Read actual exported text, not only exit status.
- [x] Request one fresh reviewer to inspect all implementation and the Review Focus above, then fix consequential findings with regression tests.
- [x] Re-run affected checks and leave implementation in the current workspace; do not push, publish, or modify the source repositories.
