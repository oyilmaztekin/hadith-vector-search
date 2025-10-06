"""Storage helpers for scraper outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import BookIndexEntry, HadithRecord


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_book_records(records: Iterable[HadithRecord], path: Path) -> int:
    ensure_parent(path)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json())
            handle.write("\n")
            count += 1
    return count


def write_book_index(entries: Iterable[BookIndexEntry], path: Path) -> None:
    ensure_parent(path)
    payload = [entry.model_dump(mode="json") for entry in entries]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html_snapshot(html: str, path: Path) -> None:
    ensure_parent(path)
    path.write_text(html, encoding="utf-8")
