# Islamic Text Hybrid Retrieval Engine & MCP Server

A high-performance retrieval engine and **Model Context Protocol (MCP)** server for Islamic corpora (Hadith & Tafsir). The system combines semantic vector search (**ChromaDB** with multilingual sentence embeddings) and lexical full-text search (**SQLite FTS5**) with an intent-aware re-ranking pipeline designed for high-precision RAG (Retrieval-Augmented Generation).

---

## Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │    AI Clients / Consumers              │
                      │  (ChatGPT MCP, Claude Desktop, Cursor) │
                      └──────────────────┬─────────────────────┘
                                         │ JSON-RPC / MCP Protocol
                                         ▼
                      ┌────────────────────────────────────────┐
                      │            MCP Server Layer            │
                      │   - Stdio Transport (FastMCP / stdio)  │
                      │   - HTTP / REST Transport (Flask)      │
                      └──────────────────┬─────────────────────┘
                                         │ Query Dispatch
                                         ▼
                      ┌────────────────────────────────────────┐
                      │       Query Intent Router              │
                      │  (Exact Match / Semantic / Balanced)   │
                      └──────────────┬──────────────────┬──────┘
                                     │                  │
                    ┌────────────────▼────┐        ┌────▼────────────────┐
                    │ Lexical Search      │        │ Semantic Search     │
                    │ SQLite FTS5         │        │ ChromaDB            │
                    │ (BM25, Narrator,    │        │ (Multilingual       │
                    │  Exact Hadith Ref)  │        │  Sentence-MPNet)    │
                    └────────────────┬────┘        └────┬────────────────┘
                                     │                  │
                                     └─────────┬────────┘
                                               ▼
                              ┌────────────────────────────────┐
                              │ Dynamic Hybrid Re-Ranker       │
                              │ - Normalized Dense/Sparse RRF  │
                              │ - Narrator Attribution Boost   │
                              │ - Phrase Match Coverage Bonus  │
                              └────────────────┬───────────────┘
                                               ▼
                              ┌────────────────────────────────┐
                              │ Ranked Hadith / Tafsir Context │
                              └────────────────────────────────┘
```

---

## Key Features

- **Hybrid Retrieval (Dense + Sparse)**: Blends semantic similarity with lexical exact-match signals to resolve both conceptual topics and specific chain-of-narration / hadith reference queries.
- **Model Context Protocol (MCP) First**: Seamlessly plug into MCP-enabled AI interfaces like Claude Desktop and ChatGPT.
- **Multilingual Support**: Supports queries across Arabic and English using multilingual sentence-transformer models (`paraphrase-multilingual-mpnet-base-v2` and `all-MiniLM-L6-v2`).
- **Domain-Specific Re-ranking**: Boosts scores based on narrator attribution, term coverage, and exact Arabic/English phrase alignments.
- **Data Ingestion & Scrapers**: Includes robust parsers for bilingual hadith datasets (Sunnah.com) and Ibn Kathir Tafsir.

---

## Project Structure

```
├── mcp_server/         # MCP Server for Hadith (Riyad as-Salihin, etc.)
│   ├── apps/           # Search backend: embeddings, SQLite FTS, scoring, router
│   ├── http_server.py  # HTTP REST API server
│   ├── mcp_stdio.py    # MCP stdio interface for LLM clients
│   └── tools.py        # Core search and status tool handlers
├── quran_mcp/          # FastMCP server for Quran & Ibn Kathir Tafsir
├── sunnah_scraper/     # Web scraping pipeline for Sunnah.com
├── quran_scraper/      # Scraper/processor for Tafsir texts
└── data/               # Corpora and SQLite/ChromaDB indexes
```

---

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/oyilmaztekin/hadith-vector-search.git
cd hadith-vector-search

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Ingest Data & Build Indexes

```bash
# Ingest and validate Hadith collection
python -m mcp_server.apps.ingestion

# Build or update vector & FTS indexes
python -m mcp_server.apps.ingestion --update-indexes
```

### 3. Run MCP Server

#### For Claude Desktop / MCP Clients (Stdio Mode)
```bash
python3 -m mcp_server.mcp_stdio
```

#### Run Tafsir MCP Server
```bash
python3 -m quran_mcp.mcp_http --host 127.0.0.1 --port 8000 --path /mcp
```

#### Run REST / HTTP API
```bash
python3 -m mcp_server.http_server --host 127.0.0.1 --port 8000
```

---

## Available MCP Tools

| Tool | Description |
|---|---|
| `hybrid_search` | Execute hybrid search across Hadith corpus with configurable weights and modes (`balanced`, `semantic`, `exact`). |
| `fts_match` | Fast lexical search matching narrators, Arabic text, or English translations. |
| `search_tafsir` | Hybrid search across Ibn Kathir Tafsir passages. |
| `get_verse` | Fetch Tafsir by Surah and Ayah / verse key. |
| `vector_index_status` / `fts_status` | Index health checks and document statistics. |

---

## Integration with Claude Desktop

Add the following to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "hadith-search": {
      "command": "python3",
      "args": ["-m", "mcp_server.mcp_stdio"],
      "cwd": "/path/to/hadith-vector-search"
    },
    "quran-tafsir": {
      "command": "python3",
      "args": ["-m", "quran_mcp.mcp_stdio"],
      "cwd": "/path/to/hadith-vector-search"
    }
  }
}
```

---

## License

This project is open-source under the [MIT License](LICENSE).
