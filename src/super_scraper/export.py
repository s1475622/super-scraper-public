"""Write unique run folders, preserving successes and failures together."""

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .models import ScrapeResult


def _csv_value(value):
    if isinstance(value, list):
        value = ";".join(value)
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_results(results: list[ScrapeResult], base: Path) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    folder = base / f"{timestamp}_{uuid4().hex[:8]}"
    folder.mkdir()
    (folder / "text").mkdir()
    (folder / "markdown").mkdir()
    records = [result.as_dict() for result in results]
    (folder / "articles.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (folder / "articles.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        fieldnames = list(ScrapeResult.__dataclass_fields__)
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            {name: _csv_value(value) for name, value in row.items()} for row in records
        )
    for index, result in enumerate(results, 1):
        if result.status != "success" or not result.text:
            continue
        digest = hashlib.sha256(result.url.encode("utf-8")).hexdigest()[:12]
        stem = f"{index:04d}_{digest}"
        source = result.final_url or result.url
        warning = f"品質提示：{', '.join(result.warnings)}\n" if result.warnings else ""
        heading = f"{result.title or '未提供標題'}\n來源：{source}\n{warning}\n"
        (folder / "text" / f"{stem}.txt").write_text(heading + result.text + "\n", encoding="utf-8")
        (folder / "markdown" / f"{stem}.md").write_text(
            heading + result.markdown + "\n", encoding="utf-8"
        )
    return folder.resolve()
