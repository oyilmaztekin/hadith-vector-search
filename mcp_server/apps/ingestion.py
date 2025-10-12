"""Simple ingestion CLI for validating hadith JSONL books."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Iterable, List

from .models import BookStats
from .validation import ValidationIssue, validate_book


DATA_DIR = Path("data/riyadussalihin")


def iter_book_paths(book_ids: Iterable[str] | None = None) -> List[Path]:
    if book_ids is None:
        return sorted(DATA_DIR.glob("book_*.jsonl"))
    paths: List[Path] = []
    for bid in book_ids:
        file_name = "book_introduction.jsonl" if bid == "introduction" else f"book_{bid}.jsonl"
        path = DATA_DIR / file_name
        if not path.exists():
            raise FileNotFoundError(f"Book file not found: {path}")
        paths.append(path)
    return paths


def ingest_book(path: Path) -> BookStats:
    start = time.perf_counter()
    records, stats = validate_book(path)
    duration = time.perf_counter() - start
    print(stats.model_dump_json(indent=2))
    print(f"Validated {len(records)} hadiths from {path.name} in {duration:.2f}s")
    return stats


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Hadith ingestion validator")
    parser.add_argument(
        "--book",
        nargs="*",
        help="Book IDs to load (e.g., 1 2 introduction). If omitted, process all",
    )
    args = parser.parse_args(argv)

    try:
        paths = iter_book_paths(args.book)
        print(f"Processing {len(paths)} book(s) from {DATA_DIR}...\n")
        for path in paths:
            ingest_book(path)
            print("-" * 60)
    except ValidationIssue as exc:
        print(f"Validation failed: {exc}")
    except FileNotFoundError as exc:
        print(str(exc))


if __name__ == "__main__":  # pragma: no cover
    main()
