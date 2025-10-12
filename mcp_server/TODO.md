# MCP Server Implementation Milestones

## Milestone A — Validation & Ingestion (Week 1)
- [ ] `hadith.validation` module: schema checks, narrator canonicalization, bilingual text assertions
- [ ] Command-line smoke test: `python -m apps.ingestion --book 1`
- [ ] Persist ingestion stats (counts, checksum diff) to `logs/ingestion/*.json`

## Milestone B — Index Foundations (Week 1-2)
- [ ] `apps/embeddings.py`: ChromaDB client with caching by checksum
- [ ] `apps/fts.py`: create FTS5 tables and seed with Book 1 sample
- [ ] MCP tools `vector_index_status` and `fts_status`

## Milestone C — Hybrid Search Core (Week 2)
- [ ] Implement `HybridScorer.calculate_priority_score`
- [ ] Port query router heuristics (exact reference, narrator, thematic, mixed)
- [ ] Expose `hybrid_search` MCP tool returning ranked results + breakdown

## Milestone D — Benchmark & QA (Week 3)
- [ ] Integrate `TEST_QUERIES.md` into `apps/benchmark.py`
- [ ] Add `run_benchmark` MCP tool with streaming metrics
- [ ] Collect baseline benchmarks (targets: <50ms p95, >70% term coverage)

## Milestone E — Operations & Docs (Week 3-4)
- [ ] Maintenance tools (`refresh_embeddings`, `vacuum_fts`)
- [ ] Structured logging + health check endpoint
- [ ] Developer guide for MCP clients (authentication, rate limits TBD)

**Dependencies:**
- Dataset integrity confirmed post Book 8 re-scrape
- Access to embedding model `paraphrase-multilingual-mpnet-base-v2`
- SQLite compiled with FTS5 extension

Update this checklist as milestones progress.
