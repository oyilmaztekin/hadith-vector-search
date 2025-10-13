"""Simple ingestion CLI for validating hadith JSONL books."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, TYPE_CHECKING

from .models import BookStats
from .validation import ValidationIssue, validate_book


DATA_DIR = Path("data/riyadussalihin")
LOG_DIR = Path("logs/ingestion")

if TYPE_CHECKING:
    from .embeddings import EmbeddingIndex, EmbeddingUpdateResult
    from .fts import FTSIndex, FtsUpdateResult


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


def ingest_book(
    path: Path,
    embedding_index: "EmbeddingIndex" | None = None,
    fts_index: "FTSIndex" | None = None,
    force_index: bool = False,
) -> Tuple[
    BookStats,
    Optional["EmbeddingUpdateResult"],
    Optional["FtsUpdateResult"],
]:
    start = time.perf_counter()
    records, stats = validate_book(path)
    duration = time.perf_counter() - start
    print(stats.model_dump_json(indent=2))
    print(f"Validated {len(records)} hadiths from {path.name} in {duration:.2f}s")
    write_log(stats, len(records), duration)

    embedding_result = None
    fts_result = None

    if embedding_index is not None:
        embedding_result = embedding_index.upsert_documents(records, force=force_index)
        print(
            "Embedding index -> processed: {processed}, inserted: {inserted}, skipped: {skipped}, duration: {duration:.2f}s".format(
                processed=embedding_result.processed,
                inserted=embedding_result.inserted,
                skipped=embedding_result.skipped,
                duration=embedding_result.duration_seconds,
            )
        )

    if fts_index is not None:
        fts_result = fts_index.upsert_documents(records, force=force_index)
        print(
            "FTS index -> processed: {processed}, inserted: {inserted}, skipped: {skipped}, duration: {duration:.2f}s".format(
                processed=fts_result.processed,
                inserted=fts_result.inserted,
                skipped=fts_result.skipped,
                duration=fts_result.duration_seconds,
            )
        )

    return stats, embedding_result, fts_result


def write_log(stats: BookStats, record_count: int, duration: float) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat().replace(":", "-")
    payload = {
        **stats.model_dump(),
        "validated_count": record_count,
        "duration_seconds": round(duration, 3),
        "timestamp": timestamp,
    }
    log_path = LOG_DIR / f"{stats.book_id}_{timestamp}.json"
    with log_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Hadith ingestion validator")
    parser.add_argument(
        "--book",
        nargs="*",
        help="Book IDs to load (e.g., 1 2 introduction). If omitted, process all",
    )
    parser.add_argument(
        "--update-indexes",
        action="store_true",
        help="Update the vector and FTS indexes after validating each book",
    )
    parser.add_argument(
        "--force-index-refresh",
        action="store_true",
        help="Force reindexing even if checksums match (implies --update-indexes)",
    )
    args = parser.parse_args(argv)

    try:
        paths = iter_book_paths(args.book)
        print(f"Processing {len(paths)} book(s) from {DATA_DIR}...\n")

        update_indexes = args.update_indexes or args.force_index_refresh
        embedding_index = None
        fts_index = None
        if update_indexes:
            from .embeddings import EmbeddingIndex
            from .fts import FTSIndex

            embedding_index = EmbeddingIndex()
            fts_index = FTSIndex()

        embedding_totals = {
            "processed": 0,
            "inserted": 0,
            "skipped": 0,
            "duration": 0.0,
        }
        fts_totals = {
            "processed": 0,
            "inserted": 0,
            "skipped": 0,
            "duration": 0.0,
        }

        for path in paths:
            _, embedding_result, fts_result = ingest_book(
                path,
                embedding_index=embedding_index,
                fts_index=fts_index,
                force_index=args.force_index_refresh,
            )
            if embedding_result is not None:
                embedding_totals["processed"] += embedding_result.processed
                embedding_totals["inserted"] += embedding_result.inserted
                embedding_totals["skipped"] += embedding_result.skipped
                embedding_totals["duration"] += embedding_result.duration_seconds
            if fts_result is not None:
                fts_totals["processed"] += fts_result.processed
                fts_totals["inserted"] += fts_result.inserted
                fts_totals["skipped"] += fts_result.skipped
                fts_totals["duration"] += fts_result.duration_seconds
            print("-" * 60)

        if update_indexes:
            print("\nIndex update summary:")
            print(
                "Embedding index totals -> processed: {processed}, inserted: {inserted}, "
                "skipped: {skipped}, duration: {duration:.2f}s".format(
                    processed=embedding_totals["processed"],
                    inserted=embedding_totals["inserted"],
                    skipped=embedding_totals["skipped"],
                    duration=embedding_totals["duration"],
                )
            )
            print(
                "FTS index totals -> processed: {processed}, inserted: {inserted}, "
                "skipped: {skipped}, duration: {duration:.2f}s".format(
                    processed=fts_totals["processed"],
                    inserted=fts_totals["inserted"],
                    skipped=fts_totals["skipped"],
                    duration=fts_totals["duration"],
                )
            )
    except ValidationIssue as exc:
        print(f"Validation failed: {exc}")
    except FileNotFoundError as exc:
        print(str(exc))


if __name__ == "__main__":  # pragma: no cover
    main()
