# Project Overview

This project is a Python-based web scraper and search server for hadith collections from Sunnah.com. The project is divided into two main components:

1.  **`sunnah_scraper`**: A web scraper that harvests hadith collections from Sunnah.com, including bilingual text and rich metadata.
2.  **`mcp_server`**: A "Model Context Protocol" server that provides a hybrid search over the scraped hadith data, using a combination of vector search (ChromaDB) and full-text search (SQLite FTS5).

## Building and Running

### `sunnah_scraper`

To run the scraper:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m sunnah_scraper.cli
```

You can also limit the scraping to specific books:

```bash
python -m sunnah_scraper.cli --book 1 --book 2
```

### `mcp_server`

The `mcp_server` is responsible for ingesting the scraped data and providing a search interface. To ingest the data:

```bash
python -m mcp_server.apps.ingestion
```

To update the search indexes:

```bash
python -m mcp_server.apps.ingestion --update-indexes
```

## Development Conventions

*   The project uses `pydantic` for data modeling and validation.
*   The `selectolax` library is used for HTML parsing.
*   `requests` is used for making HTTP requests.
*   `tenacity` is used for retries.
*   `chromadb` is used for vector storage.
*   `sentence-transformers` is used for generating embeddings.
*   `sqlite` with FTS5 is used for full-text search.
*   The code is well-documented with comments and docstrings.
*   The project includes a `README.md` file with detailed instructions.
