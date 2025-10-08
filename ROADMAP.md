# Sunnah.com Hadith Search Roadmap

A staged plan to evolve the Riyad as-Salihin scraper into a production-ready search system that blends fast term matching with semantic retrieval.

## Phase 0 — Baseline (✅ current)
- Structured JSONL export with Arabic + English texts, chapter metadata, and references
- HTML snapshots stored for reparsing
- One-click scraper CLI with book filtering and retry logic

## Phase 1 — Local Index Foundations
1. **Data Normalization**
   - [ ] Create a lightweight ingestion script that loads JSONL into Python objects
   - [ ] Preserve canonical IDs (`collection:book:hadith`) and metadata attributes
2. **Vector Store Setup**
   - [ ] Encode hadith texts (EN+AR concatenated) with `all-MiniLM-L6-v2`
   - [ ] Persist embeddings + metadata in ChromaDB (local disk)
   - [ ] Record checksums to skip unchanged entries on re-scrape
3. **Full-Text Index**
   - [ ] Build a SQLite database with FTS5 tables for English text and keyword fields (book, narrator)
   - [ ] Optionally add transliterated Arabic terms for fallback matching

## Phase 2 — Hybrid Retrieval Prototype
1. **Query Parsing**
   - [ ] Tokenize queries, preserving abbreviations and Arabic script
   - [ ] Generate a semantic embedding for each query
2. **Candidate Retrieval**
   - [ ] Run FTS search to obtain top-N term matches with coverage scores
   - [ ] Run vector search to obtain top-M semantic candidates from ChromaDB
3. **Scoring & Fusion**
   - [ ] Implement a term-priority scoring function combining cosine similarity with term coverage
   - [ ] Boost results that match all query tokens or key phrases
4. **CLI Proof-of-Concept**
   - [ ] Expose a command-line search tool that prints ranked results with metadata snippets

## Phase 3 — Service Layer & UX
1. **API Wrapper**
   - [ ] Build a FastAPI (or Flask) service for search and document retrieval endpoints
   - [ ] Add pagination, language filters, and ability to retrieve full hadith context
2. **Caching & Performance**
   - [ ] Implement in-memory caching for frequent queries and embeddings
   - [ ] Monitor latency; target <150ms p95 end-to-end on CPU-only hardware
3. **Explainability**
   - [ ] Return term coverage and similarity metrics with each result
   - [ ] Flag whether a result came via term match, semantic match, or both

## Phase 4 — Quality & Expansion
1. **Evaluation Harness**
   - [ ] Compile a benchmark set of typical user queries (Arabic, English, transliterated)
   - [ ] Measure precision/recall against curated ground truth
2. **Continuous Re-Scraping**
   - [ ] Automate scraper runs with change detection and delta ingestion
   - [ ] Alert on failed fetches or schema changes (CSS selector drift)
3. **Corpus Growth**
   - [ ] Add additional collections (e.g., Sahih Bukhari, Muslim) using same pipeline
   - [ ] Track collection-specific metadata (gradings, numbering schemes)
4. **Optional Enhancements**
   - [ ] Explore multilingual embedding upgrades (`paraphrase-multilingual-mpnet-base-v2`) if Arabic-only queries grow
   - [ ] Add synonym/abbreviation dictionary (e.g., `PAT → Personal Access Token` equivalent for hadith terminology)

## Phase 5 — Production Hardening
- [ ] Containerize scraper + indexer + API for deployment
- [ ] Integrate observability (structured logs, metrics)
- [ ] Develop automated regression tests for parsing and retrieval ranking
- [ ] Document operational runbooks and failure recovery procedures

---

**Key Principles**
- Stay local-first: keep storage and inference on affordable hardware
- Preserve original text fidelity (Arabic diacritics, transliteration) while enabling normalization
- Design for incremental expansion: new collections plug into the same ingestion and indexing pipeline
- Validate ranking changes against real queries before promotion
