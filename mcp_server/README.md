# Hadith MCP Server Scaffold

This document describes the initial blueprint for the Model Context Protocol server that will power hybrid search over the Riyad as-Salihin corpus. It captures the core capabilities, tool endpoints, and immediate implementation tasks derived from `HADITH_SEARCH_SPEC.md`, `TEST_QUERIES.md`, and `ANALYSIS_SUMMARY.md`.

## 1. Core Responsibilities
- Normalize JSONL hadith records into canonical objects with checksum-based change detection (`HADITH_SEARCH_SPEC.md:63`).
- Maintain dual indexes: ChromaDB for embeddings (multilingual) and SQLite FTS5 for exact references (`HADITH_SEARCH_SPEC.md:261`, `TEST_QUERIES.md:33`).
- Run the hybrid scoring pipeline that blends semantic similarity with narrator/term/phrase bonuses (`HADITH_SEARCH_SPEC.md:463`).
- Serve benchmark and diagnostics utilities for the 86-query evaluation suite (`TEST_QUERIES.md:370`).

## 2. Planned MCP Tools
| Tool Name | Purpose | Input | Output |
|-----------|---------|-------|--------|
| `ingest_book` | Load a specific JSONL book, return stats, detect anomalies | `{"book_id": "8"}` | Counts, checksum summary, validation warnings |
| `ingest_all` | Batch ingestion of all books with cached checksum skip | `{}` | Aggregate counts + list of skipped/ingested books |
| `vector_index_status` | Report embedding index metadata (dimensions, doc count, last updated) | `{}` | Status dict |
| `fts_status` | Report SQLite FTS integrity, row counts, sample entries | `{}` | Status dict |
| `hybrid_search` | Execute full hybrid search (router + scorer) | `{ "query": str, "n_results": int }` | Ranked hits with score breakdown |
| `rerank_candidates` | Accept pre-fetched candidates and apply priority scoring | `{ "query": str, "candidates": [...] }` | Re-ranked list + explanations |
| `run_benchmark` | Execute predefined query suite, stream metrics | `{ "category": str|null }` | Benchmark report + per-query metrics |
| `maintenance.refresh_embeddings` | Regenerate embeddings for stale checksums | `{ "book_ids": [...] }` | Regeneration log |
| `maintenance.vacuum_fts` | Optimize FTS tables | `{}` | Result summary |

## 3. Server Architecture Sketch
```
apps/
  ingestion.py       # JSONL -> HadithDocument + validation
  embeddings.py      # ChromaDB client wrapper
  fts.py             # SQLite FTS5 schema + helpers
  scoring.py         # Hybrid scoring + explanations
  router.py          # Query intent classification
  benchmark.py       # TEST_QUERIES runner
mcp_server.py        # MCP server entrypoint registering tools
config/
  settings.py        # Paths, model names, thresholds
  logging.py         # Structured logging helpers
http_server.py       # Flask HTTP server exposing MCP endpoints
```

## 4. Implementation Sequencing
1. **Data Integrity Gate**
   - Re-run validator post Book 8 fix (`data_quality_report.json`).
   - Implement reusable validation module for MCP ingestion tools.
2. **Ingestion Layer**
   - Define `HadithDocument` dataclass with canonical narrator normalization.
   - Build JSONL streaming loader with checksum caching (Phase 1 requirement).
3. **Index Services**
   - Initialize ChromaDB using `paraphrase-multilingual-mpnet-base-v2`.
   - Create SQLite FTS5 schema (`hadith`, `narrators`, `chapters`).
   - Add maintenance hooks for re-embedding and vacuuming.
4. **Hybrid Scoring Engine**
   - Port scoring weights from spec (`HADITH_SEARCH_SPEC.md:463`).
   - Include narrator/phrase bonuses and grading placeholder with fallbacks.
5. **MCP Tool Registration**
   - Expose ingestion + status tools first for incremental testing.
   - Add `hybrid_search` once scoring passes smoke tests.
6. **Benchmark Harness**
   - Wire `run_benchmark` to TEST_QUERIES categories, capturing metrics listed in the spec.
7. **Observability + Docs**
   - Structured logging, health checks, and README updates for client integration.

## 5. Immediate Action Items
- ✅ Confirm Book 8 encoding repair and updated `index.json` (user fix complete).
- 🔲 Implement validation utilities for JSONL ingestion.
- 🔲 Draft `HadithDocument` dataclass and narrator normalization helper.
- 🔲 Prototype MCP server entrypoint with placeholder tools returning `NotImplemented`.
- 🔲 Define configuration module (paths, embedding model names, thresholds).

## 7. MCP Servers

Two ways to integrate with MCP clients:

- Python stdio MCP (requires Python ≥ 3.10 + python SDK):
  - Install: `python3 -m pip install "git+https://github.com/modelcontextprotocol/python-sdk.git#egg=mcp"`
  - Run Inspector: `npx -y @modelcontextprotocol/inspector --command "python3 -m mcp_server.mcp_stdio"`
  - ChatGPT MCP connection: Command `python3`, Args `-m`, `mcp_server.mcp_stdio`.

- Node stdio MCP bridge (no Python SDK requirement):
  - In repo root: `npm init -y && npm i @modelcontextprotocol/sdk`
  - Run Inspector: `npx -y @modelcontextprotocol/inspector --command "node mcp_server/js/mcp-server.mjs"`
  - ChatGPT MCP connection:
    - Command: `node`
    - Arguments: `mcp_server/js/mcp-server.mjs`
    - Working directory: repo root (so Python can import `mcp_server`)
    - Optional env: `PYTHONPATH` set to repo root; ensure `python3` in PATH

Available tools (both servers):
- `hybrid_search` { query, n_results?, mode?, collection?, weight_*?, bonus_phrase? }
- `fts_status` { collection? }
- `vector_index_status` { collection? }
- `fts_match` { match? | en?/ar?/narrator?, limit?, collection? }

## 6. Open Questions
1. Should authentication or rate limiting be part of the MCP interface?
2. Will the server manage embeddings lazily (on demand) or during ingestion?
3. Where should benchmark results be persisted (JSONL log vs database)?

This scaffold will evolve as components are implemented. Update the task checklist above as milestones are completed.

## Current Status
- ✅ `mcp_server/apps/models.py`: Pydantic models with narrator normalization and bilingual validation
- ✅ `mcp_server/apps/validation.py`: JSONL loader + stats collector (Book 8 fix verified)
- ✅ `python -m mcp_server.apps.ingestion --book 1`: CLI for per-book validation/stats (writes logs under `logs/ingestion/`)
- ⬜ Index services, hybrid scorer, MCP tool registration (next milestones)

### Usage Snapshot
```bash
# Validate a single book
python -m mcp_server.apps.ingestion --book 1

# Validate the full corpus (may take ~30s depending on disk)
python -m mcp_server.apps.ingestion

# Run HTTP server (Flask)
python -m mcp_server.http_server --host 127.0.0.1 --port 8000

# Example calls
curl 'http://127.0.0.1:8000/api/riyadussalihin/status/fts'
curl 'http://127.0.0.1:8000/api/riyadussalihin/status/vector'
curl -X POST 'http://127.0.0.1:8000/api/riyadussalihin/search/hybrid' \
     -H 'Content-Type: application/json' \
     -d '{"query": "narrated by Abu Hurairah", "n_results": 5, "mode": "balanced"}'
```
