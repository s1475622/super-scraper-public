"""Compare local benchmark exports with independently selected source blocks.

A fetch success is not a quality pass. Public profiles and the Reuters category
control are reported separately from articles. No article copy is written to
the verification report; raw pages and exports remain ignored local artifacts.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup, Comment

FORBIDDEN = {
    "reporter": ["載入更多文章", "立即支持"],
    "technews": ["喝杯咖啡", "訂閱免費電子報", "想請我們喝幾杯"],
    "tvbs": ["公務員爭離線權", "網銀帳戶被盜轉", "MAMA2026卡司", "GliaStudios", "NEXT VIDEO"],
    "setn": ["熱搜新聞", "其他人也在看", "加入Google首選"],
    "pansci": ["耐污馬桶的表面科學", "脂肪肝不只靠減肥", "Recommended by", "廣告，請繼續往下閱讀"],
    "nike": ["Nike Air Has Scaled Across Sports for Decades"],
    "guardian": ["Explore more on these topics", "Reuse this content"],
    "apple": ["新聞聯絡人", "Apple 媒體聯絡人"],
    "lrp": [
        "回首頁",
        "點擊看更多",
        "看解答",
        "實體銷售據點",
        "登入會員領試用",
        "恭喜您已成功領取試用品",
    ],
}


def key(value):
    value = re.sub(r"</?(?:sup|sub|strong|em|span)\b[^>]*>", "", value)
    return re.sub(r"\s+", "", value).replace("*", "").replace("__", "").replace("\\", "")


def source_blocks(sample, path):
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for node in soup.select("script,style,nav,footer,aside,[hidden],[aria-hidden='true']"):
        if node.parent is not None:
            node.decompose()
    evidence = sample["evidence"]
    if evidence.get("exclude"):
        for node in soup.select(evidence["exclude"]):
            if node.parent is not None:
                node.decompose()
    nodes = soup.select(evidence["selector"])
    strings = (
        [
            str(text)
            for node in nodes
            for text in node.find_all(string=True)
            if not isinstance(text, Comment)
        ]
        if evidence["kind"] == "leaf_text"
        else [node.get_text() for node in nodes]
    )
    return list(dict.fromkeys(text for text in strings if len(key(text)) >= evidence["minimum"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", default="final")
    parser.add_argument("--manifest", type=Path, default=Path("examples/extended-sites.json"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/extended-sites"))
    parser.add_argument("--output", type=Path, default=Path("output/extended-sites"))
    args = parser.parse_args()
    samples = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    report, regressions = {"modes": {}, "best_outcomes": []}, []
    best = {sample["id"]: [] for sample in samples}
    for mode in ("http", "browser"):
        cache = args.cache / args.phase / mode
        folder = Path((cache / "export.txt").read_text(encoding="utf-8"))
        records = json.loads((folder / "articles.json").read_text(encoding="utf-8"))
        if [row["url"] for row in records] != [sample["url"] for sample in samples]:
            raise SystemExit(f"Manifest/export URL mismatch: {mode}")
        results = []
        for sample, row in zip(samples, records, strict=True):
            item = {name: sample[name] for name in ("id", "site", "category", "page_type", "url")}
            item.update({name: row[name] for name in ("status", "char_count", "warnings", "error")})
            if row["status"] != "success":
                item["outcome"] = (
                    "access_blocked"
                    if (row["error"] or "").startswith(("http_403:", "robots_disallowed:"))
                    else "fetch_error"
                )
            elif "evidence" not in sample:
                item["outcome"] = "partial_unverified"
            else:
                expected = source_blocks(sample, cache / f"{sample['id']}.html")
                item["source_blocks"] = len(expected)
                complete = bool(expected)
                for field in ("text", "markdown"):
                    actual = key(row[field])
                    hits = sum(key(text) in actual for text in expected)
                    item[f"{field}_blocks"] = f"{hits}/{len(expected)}"
                    if hits != len(expected) or not expected:
                        complete = False
                        regressions.append(f"{mode}/{sample['id']}/{field}: {hits}/{len(expected)}")
                leaked = [
                    phrase
                    for phrase in FORBIDDEN.get(sample["id"], [])
                    if key(phrase) in key(row["text"])
                ]
                if leaked:
                    complete = False
                    regressions.append(f"{mode}/{sample['id']}: known UI/recommendation leaked")
                quality_warnings = set(row["warnings"]) - {"robots_unavailable"}
                item["outcome"] = (
                    "verified_core" if complete and not quality_warnings else "partial_unverified"
                )
            best[sample["id"]].append(item["outcome"])
            results.append(item)
        report["modes"][mode] = {
            "export": str(folder),
            "counts": dict(Counter(row["outcome"] for row in results)),
            "results": results,
        }
    for sample in samples:
        outcomes = best[sample["id"]]
        outcome = (
            "verified_core"
            if "verified_core" in outcomes
            else "partial_unverified"
            if "partial_unverified" in outcomes
            else "access_blocked"
            if all(value == "access_blocked" for value in outcomes)
            else "fetch_error"
        )
        report["best_outcomes"].append(
            {"id": sample["id"], "category": sample["category"], "outcome": outcome}
        )
    report["regressions"] = regressions
    destination = args.output / args.phase / "verification.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for mode, data in report["modes"].items():
        print(mode, data["counts"])
        for row in data["results"]:
            print(
                row["id"],
                row["outcome"],
                row["char_count"],
                row.get("text_blocks", ""),
                row.get("markdown_blocks", ""),
            )
    print("REGRESSIONS", regressions)
    print("REPORT", destination)
    return 1 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
