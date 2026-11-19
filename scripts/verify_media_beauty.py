"""Audit live exports against saved source HTML, independently of the extractor.

The HTML cache and crawl exports are local investigation artifacts, not fixtures
distributed with the project. Run after the two crawl commands in the report.
"""

import argparse
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


def key(value):
    return re.sub(r"\s+", "", value).replace("**", "").replace("__", "").replace("\\", "")


def latest(root):
    files = sorted(root.glob("*/articles.json"))
    if not files:
        raise SystemExit(f"Missing crawl exports: {root}")
    return files[-1]


def evidence(html_root):
    expected = {}
    for index in (4, 5, 8):
        soup = BeautifulSoup(
            (html_root / f"{index}.html").read_text(encoding="utf-8"), "html.parser"
        )
        headings = []
        if index == 4:
            headings = [
                node
                for node in soup.select('[data-theme-key="listicle-slide-item-title"]')
                if node.get_text().startswith("保濕化妝水推薦")
            ]
            slides = [
                node.find_parent(attrs={"data-journey-listicle-slide": True}) for node in headings
            ]
            paragraphs = [node for slide in slides for node in slide.select("p")]
            paragraphs = [
                node
                for node in paragraphs
                if not node.select_one('a[data-vars-ga-call-to-action^="點選連結看更多"]')
            ]
        elif index == 5:
            # Independently exclude recommendations and hidden marketing; keep
            # editorial caption paragraphs as well as ordinary body paragraphs.
            for node in soup.select(
                '[aria-hidden="true"], [data-testid="external-link-embed--inline"], .article-body__footer'
            ):
                if node.parent is not None:
                    node.decompose()
            headings = [
                node
                for node in soup.select('[role="heading"][aria-level="3"]')
                if re.match(r"^\d+\.", node.get_text(strip=True))
            ]
            paragraphs = soup.select(".body__inner-container p")
        else:
            paragraphs = soup.select("[data-fp-embedded-gallery-product] p")
        copy = [
            re.sub(r"See more details\s*$", "", node.get_text(), flags=re.I).strip()
            for node in paragraphs
        ]
        expected[index] = {
            "headings": [node.get_text() for node in headings],
            "paragraphs": [value for value in copy if len(key(value)) >= 4],
        }
    counts = [(len(item["headings"]), len(item["paragraphs"])) for item in expected.values()]
    if counts != [(15, 33), (20, 50), (0, 128)]:
        raise SystemExit(f"Source structure changed; review evidence selectors: {counts}")
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html-root", type=Path, default=Path(".cache/media-beauty-html"))
    parser.add_argument("--result-root", type=Path, default=Path("output/media-beauty-repaired"))
    parser.add_argument("--baseline-root", type=Path, default=Path("output/media-beauty/http"))
    args = parser.parse_args()
    expected = evidence(args.html_root)
    baseline = json.loads(latest(args.baseline_root).read_text(encoding="utf-8"))
    urls = [row["url"] for row in baseline]
    failures, summary, texts = [], {}, {}
    for mode in ("http", "browser"):
        source = latest(args.result_root / mode)
        rows = json.loads(source.read_text(encoding="utf-8"))
        if [row["url"] for row in rows] != urls or len(rows) != 8:
            raise SystemExit(f"Unexpected URL list in {source}")
        summary[mode] = {"export": str(source), "articles": []}
        texts[mode] = [row.get("text", "") for row in rows]
        for index, row in enumerate(rows, 1):
            item = {
                "site": index,
                "status": row["status"],
                "char_count": row.get("char_count"),
                "warnings": row.get("warnings", []),
            }
            if row["status"] != "success" or row.get("warnings") or not row.get("title"):
                failures.append(f"{mode}/{index}: fetch or metadata quality failure")
            for field in ("text", "markdown"):
                actual = key(row.get(field, ""))
                groups = expected.get(index)
                if groups is None:
                    # News: retain all substantial original paragraphs. The
                    # title may legitimately move from text to its metadata field.
                    # Other two beauty sites: spot-check the original opening.
                    lines = [
                        line
                        for line in baseline[index - 1]["text"].splitlines()
                        if len(key(line)) >= 40
                    ]
                    groups = {"baseline_paragraphs": lines if index <= 3 else lines[:1]}
                for label, values in groups.items():
                    found = sum(key(value) in actual for value in values)
                    item[f"{field}_{label}"] = f"{found}/{len(values)}"
                    if found != len(values):
                        failures.append(f"{mode}/{index}/{field}/{label}: {found}/{len(values)}")
                    elif label == "headings":
                        positions = [actual.index(key(value)) for value in values]
                        if positions != sorted(positions):
                            failures.append(
                                f"{mode}/{index}/{field}: product heading order changed"
                            )
            if any(
                phrase in row.get("text", "")
                for phrase in (
                    "Watch Next",
                    "點選連結看更多美妝",
                    "立即加好友",
                    "別錯過精彩內容",
                    "個人化推薦",
                    "by Taboola",
                    "你可能感興趣",
                )
            ):
                failures.append(f"{mode}/{index}: known promotion leaked")
            summary[mode]["articles"].append(item)
    summary["identical_text_between_modes"] = texts["http"] == texts["browser"]
    summary["failures"] = failures
    destination = args.result_root / "verification.json"
    destination.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
