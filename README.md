# Sunnah.com Hadith Scraper

Prototype scraper for harvesting hadith collections from [Sunnah.com](https://sunnah.com/) with bilingual text and rich metadata suitable for RAG pipelines or classical search. The initial focus is the *Riyad as-Salihin* collection, but the pipeline is structured so other collections can be enabled by changing the collection slug.

## Features

- Walks collection index pages to discover book links automatically.
- Captures Arabic source text, English translations, chapter metadata, narrator lines, and reference tables for each hadith.
- Persists validated `HadithRecord` objects as JSON Lines (one record per line) plus raw HTML snapshots for reproducibility.
- Computes per-record checksums to simplify change detection when re-scraping.

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Running the scraper (Riyad as-Salihin by default):

```bash
# Optional: avoid creating .pyc files
export PYTHONDONTWRITEBYTECODE=1

python -m sunnah_scraper.cli
```

Limit to specific books:

```bash
python -m sunnah_scraper.cli --book 1 --book 2
```

## Output Layout

- `html/<collection>/<book_id>.html` – raw page snapshot used for parsing.
- `data/<collection>/book_<book_id>.jsonl` – JSON Lines file of `HadithRecord` entries.
- `data/<collection>/index.json` – summary of books (id, localized titles, book number, hadith count, last scrape timestamp).

Each hadith record includes:

- `collection_slug`, `collection_name`
- `book_id`, `book_title_en`, `book_title_ar`
- `chapter_id`, `chapter_number_en`, `chapter_number_ar`, `chapter_title_en`, `chapter_title_ar`
- `hadith_id_site`, `hadith_num_global`, `hadith_num_in_book`
- `texts` – Arabic and English content blocks
- `narrator`, `grading`, `references`, `topics`, `footnotes`
- `source_url`, `scraped_at`, `checksum`

## Configuration Notes

- The collection slug defaults to `riyadussalihin` in `sunnah_scraper/cli.py`. Changing it (and optionally limiting books) lets you target other collections.
- `sunnah_scraper/http.py` throttles requests to roughly one per second with retry support (`tenacity`). Adjust rate limits before large-scale crawls.
- `sunnah_scraper/parser.py` contains all CSS selectors; update them if Sunnah.com's markup changes.

## Development Hints

- Saved HTML snapshots under `html/` double as fixtures for parser tests.
- The JSON schema (defined in `sunnah_scraper/models.py`) maps cleanly to future SQLite/Postgres ingestion.
- For longer runs, consider persisting ETag/Last-Modified headers or checksums to implement incremental updates.

## License

The scraper code in this repository is MIT licensed. Refer to upstream sources (e.g., Sunnah.com content and any third-party libraries) for their respective terms.
