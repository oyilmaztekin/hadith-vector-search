"""Command-line entry point for the Sunnah.com scraper prototype."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from .http import HttpClient
from .models import BookIndexEntry
from . import parser, storage

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

BASE_URL = "https://sunnah.com"
COLLECTION_SLUG = "riyadussalihin"
COLLECTION_URL = f"{BASE_URL}/{COLLECTION_SLUG}"

DATA_ROOT = Path("data") / COLLECTION_SLUG
HTML_ROOT = Path("html") / COLLECTION_SLUG


def run_collection_scrape(book_filter: Sequence[str] | None = None) -> None:
    LOGGER.info("Fetching collection index from %s", COLLECTION_URL)
    with HttpClient() as client:
        collection_html = client.fetch_text(COLLECTION_URL)
        collection_name, index_entries = parser.parse_collection_index(
            collection_html,
            COLLECTION_SLUG,
            COLLECTION_URL,
        )
        resolved_collection_name = collection_name or COLLECTION_SLUG.replace("-", " ").title()
        if book_filter:
            index_entries = [entry for entry in index_entries if entry.book_id in book_filter]
        updated_entries: list[BookIndexEntry] = []
        for entry in index_entries:
            LOGGER.info("Processing book %s", entry.book_id)
            book_html = client.fetch_text(entry.source_url)
            snapshot_path = HTML_ROOT / f"{entry.book_id}.html"
            storage.write_html_snapshot(book_html, snapshot_path)
            (
                parsed_book_title_en,
                parsed_book_title_ar,
                parsed_book_number,
                hadith_records,
            ) = parser.parse_book_page(
                book_html,
                collection_slug=COLLECTION_SLUG,
                collection_name=resolved_collection_name,
                book_id=entry.book_id,
                book_url=entry.source_url,
                fallback_book_title_en=entry.book_title_en,
            )
            book_path = DATA_ROOT / f"book_{entry.book_id}.jsonl"
            written = storage.write_book_records(hadith_records, book_path)
            LOGGER.info("Wrote %d hadith records for book %s", written, entry.book_id)
            updated_entries.append(
                entry.model_copy(update={
                    "book_number": parsed_book_number,
                    "book_title_en": parsed_book_title_en,
                    "book_title_ar": parsed_book_title_ar,
                    "hadith_count": written,
                })
            )
        storage.write_book_index(updated_entries, DATA_ROOT / "index.json")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser_obj = argparse.ArgumentParser(description="Scrape Sunnah.com Riyad as-Salihin")
    parser_obj.add_argument(
        "--book",
        dest="books",
        action="append",
        help="Limit scraping to specific book_id values (can be used multiple times).",
    )
    return parser_obj.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    run_collection_scrape(book_filter=args.books)


if __name__ == "__main__":  # pragma: no cover
    main()
