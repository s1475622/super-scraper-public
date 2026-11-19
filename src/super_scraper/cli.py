"""Local command-line entry point."""

import argparse
import logging
import sys
from pathlib import Path

from .export import export_results
from .inputs import collect_urls
from .models import DependencyError, Options
from .pipeline import run_batch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="super-scraper",
        description="擷取文章正文，批次匯出 JSON、CSV、TXT 與 Markdown。",
    )
    parser.add_argument("urls", nargs="*", help="單個或多個完整文章網址")
    parser.add_argument("--file", type=Path, help="UTF-8 網址清單，每行一個網址")
    parser.add_argument(
        "--output", type=Path, default=Path("output"), help="輸出根目錄（預設 output）"
    )
    parser.add_argument(
        "--mode", choices=["http", "browser"], default="http", help="browser 模式可執行 JavaScript"
    )
    parser.add_argument(
        "--timeout", type=float, default=20, help="每次網路操作的逾時秒數（預設 20）"
    )
    parser.add_argument("--delay", type=float, default=1, help="兩個網址間的等待秒數（預設 1）")
    parser.add_argument(
        "--retries", type=int, default=2, help="暫時失敗的額外重試次數，0–5（預設 2）"
    )
    parser.add_argument(
        "--max-bytes", type=int, default=10 * 1024 * 1024, help="HTML 大小上限（預設 10 MiB）"
    )
    parser.add_argument(
        "--wait-ms", type=int, default=2000, help="瀏覽器載入後額外等待，0–10000 毫秒"
    )
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    logging.basicConfig(level=logging.CRITICAL)
    try:
        options = Options(
            mode=args.mode,
            timeout=args.timeout,
            delay=args.delay,
            retries=args.retries,
            max_bytes=args.max_bytes,
            wait_ms=args.wait_ms,
        )
        urls = collect_urls(args.urls, args.file)
        args.output.mkdir(parents=True, exist_ok=True)

        def progress(index, total, result):
            label = "成功" if result.status == "success" else "失敗"
            detail = result.error or (", ".join(result.warnings) if result.warnings else "")
            print(f"[{index}/{total}] {label} {result.url} {detail}", file=sys.stderr)

        results = run_batch(urls, options, progress=progress)
        folder = export_results(results, args.output)
    except (ValueError, OSError, UnicodeError, DependencyError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("已中止；本次未完成匯出。", file=sys.stderr)
        return 130
    successes = sum(result.status == "success" for result in results)
    warnings = sum(bool(result.warnings) for result in results)
    failures = len(results) - successes
    print(f"成功 {successes} 篇，失敗 {failures} 篇，品質提示 {warnings} 篇。")
    print(f"輸出位置：{folder}")
    return 1 if failures else 0
