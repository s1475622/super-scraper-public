import csv
import json
import os
import subprocess
import sys

import pytest

ARTICLE = """<html lang="zh-Hant"><head><meta charset="utf-8"><title>批次測試文章</title>
<meta name="author" content="陳小華"></head><body><nav>不要抓取的導覽列</nav>
<article><h1>批次測試文章</h1><p>這是一篇用於測試批次擷取功能的完整文章，內容包含中文標點與段落。
第一段說明工具的主要目的，是將網站中的文章正文整理成可以分析的資料。</p>
<p>第二段提供額外細節，讓我們確認擷取結果保留了文章內容。輸出時需要使用正確的文字編碼，
才能在其他軟體開啟，而不會出現亂碼，也不會將導覽選單混入文章內容。</p></article>
<footer>不要抓取的頁尾</footer></body></html>"""


def run_cli(*args):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, "-m", "super_scraper", *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=40,
    )


def test_batch_keeps_successes_and_exports_auditable_failures(web_server, tmp_path):
    web_server.add("/one", ARTICLE)
    web_server.add("/two", ARTICLE)
    source = tmp_path / "urls.txt"
    source.write_text(
        f"{web_server.base}/one#section\n{web_server.base}/missing\n{web_server.base}/two\n",
        encoding="utf-8-sig",
    )
    output = tmp_path / "exports"
    result = run_cli("--file", source, "--output", output, "--delay", "0", "--retries", "0")
    assert result.returncode == 1, result.stderr
    folders = list(output.iterdir())
    assert len(folders) == 1
    records = json.loads((folders[0] / "articles.json").read_text(encoding="utf-8"))
    assert [r["status"] for r in records] == ["success", "error", "success"]
    assert "http_404" in records[1]["error"]
    assert records[0]["author"] == "陳小華"
    assert records[0]["published_date"] is None
    assert "第二段提供額外細節" in records[0]["text"]
    assert "不要抓取" not in records[0]["text"]
    assert records[0]["url"] == web_server.base + "/one"
    assert records[0]["extracted_at"].endswith("+00:00")
    assert (folders[0] / "articles.csv").read_bytes().startswith(b"\xef\xbb\xbf")
    with (folders[0] / "articles.csv").open(encoding="utf-8-sig", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    assert len(csv_rows) == 3
    assert csv_rows[0]["text"] == records[0]["text"]
    txts = list((folders[0] / "text").glob("*.txt"))
    assert len(txts) == 2
    assert len(list((folders[0] / "markdown").glob("*.md"))) == 2
    assert "批次測試文章" in txts[0].read_text(encoding="utf-8")
    assert web_server.hits["/robots.txt"] == 1


def test_repeat_run_uses_new_folder_and_deduplicates_urls(web_server, tmp_path):
    web_server.add("/article", ARTICLE)
    url = web_server.base + "/article"
    for _ in range(2):
        result = run_cli(url, url + "#other", "--output", tmp_path, "--delay", "0")
        assert result.returncode == 0, result.stderr
    assert len(list(tmp_path.iterdir())) == 2
    assert web_server.hits["/article"] == 2


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--timeout", "nan"],
        ["--delay", "-1"],
        ["--wait-ms", "10001"],
        ["--retries", "-1"],
        ["--max-bytes", "0"],
    ],
)
def test_invalid_global_input_fails_before_network(web_server, tmp_path, args):
    urls = [] if not args else [web_server.base + "/article"]
    result = run_cli(*urls, *args, "--output", tmp_path / "output")
    assert result.returncode == 2
    assert not web_server.hits
    assert not (tmp_path / "output").exists()


def test_bad_individual_url_is_exported_without_aborting(web_server, tmp_path):
    web_server.add("/article", ARTICLE)
    result = run_cli("bad-url", web_server.base + "/article", "--output", tmp_path, "--delay", "0")
    assert result.returncode == 1, result.stderr
    data = json.loads(next(tmp_path.glob("*/articles.json")).read_text(encoding="utf-8"))
    assert "invalid_url" in data[0]["error"]
    assert data[1]["status"] == "success"


def test_output_path_error_is_global(web_server, tmp_path):
    web_server.add("/article", ARTICLE)
    output = tmp_path / "not-a-folder"
    output.write_text("existing data", encoding="utf-8")
    result = run_cli(web_server.base + "/article", "--output", output)
    assert result.returncode == 2
    assert output.read_text(encoding="utf-8") == "existing data"


def test_robots_forbidden_is_reported_in_batch(web_server, tmp_path):
    web_server.add("/robots.txt", "User-agent: *\nDisallow: /private", content_type="text/plain")
    web_server.add("/private", ARTICLE)
    result = run_cli(web_server.base + "/private", "--output", tmp_path, "--delay", "0")
    assert result.returncode == 1
    data = json.loads(next(tmp_path.glob("*/articles.json")).read_text(encoding="utf-8"))
    assert "robots_disallowed" in data[0]["error"]
    assert web_server.hits["/private"] == 0
