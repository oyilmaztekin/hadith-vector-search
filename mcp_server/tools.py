"""High-level MCP tool functions for index status reporting and search."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path

from .apps.embeddings import EmbeddingIndex
from .apps.fts import FTSIndex
from .apps.router import route_query, build_fts_match
from .apps.scoring import HybridScorer, serialize_breakdown


def vector_index_status(collection: Optional[str] = None) -> Dict[str, Any]:
    """Return status information about the embedding (vector) index.

    If a collection is provided, resolves the corresponding index paths.
    """
    cfg = _resolve_collection_index_config(collection or "riyadussalihin")
    index = EmbeddingIndex(
        persist_directory=Path(cfg["chroma_dir"]),
        collection_name=cfg.get("chroma_collection", "hadith_documents"),
    )
    status = index.status()
    status["collection"] = cfg["name"]
    return status


def fts_status(collection: Optional[str] = None) -> Dict[str, Any]:
    """Return status information about the SQLite FTS index."""

    cfg = _resolve_collection_index_config(collection or "riyadussalihin")
    index = FTSIndex(db_path=Path(cfg["fts_db"]))
    status = index.status()
    status["collection"] = cfg["name"]
    return status


def hybrid_search(
    query: str,
    n_results: int = 10,
    *,
    mode: Optional[str] = None,
    collection: Optional[str] = None,
    weight_vector: Optional[float] = None,
    weight_fts: Optional[float] = None,
    weight_term_coverage: Optional[float] = None,
    bonus_phrase: Optional[float] = None,
) -> Dict[str, Any]:
    intent = route_query(query)

    cfg = _resolve_collection_index_config(collection or "riyadussalihin")
    fts = FTSIndex(db_path=Path(cfg["fts_db"]))
    emb = EmbeddingIndex(
        persist_directory=Path(cfg["chroma_dir"]),
        collection_name=cfg.get("chroma_collection", "hadith_documents"),
    )
    # Mode presets (can be overridden by explicit parameters)
    presets = {
        "balanced": {
            "weight_vector": 0.6,
            "weight_fts": 0.4,
            "weight_term_coverage": 0.20,
            "bonus_phrase": 0.05,
        },
        "term-priority": {
            "weight_vector": 0.30,
            "weight_fts": 0.30,
            "weight_term_coverage": 0.60,
            "bonus_phrase": 0.20,
        },
    }
    selected = presets.get(mode or "balanced", presets["balanced"])  # default to balanced

    scorer = HybridScorer(
        weight_vector=weight_vector if weight_vector is not None else selected["weight_vector"],
        weight_fts=weight_fts if weight_fts is not None else selected["weight_fts"],
        weight_term_coverage=(
            weight_term_coverage if weight_term_coverage is not None else selected["weight_term_coverage"]
        ),
        bonus_phrase=bonus_phrase if bonus_phrase is not None else selected["bonus_phrase"],
    )

    match = build_fts_match(intent)
    fts_rows = []
    try:
        fts_rows = fts.search_match(match, limit=max(50, n_results * 5))
    except Exception:
        fts_rows = []

    emb_rows = []
    if emb.dependencies_ok():
        emb_rows = emb.query(intent.normalized, n_results=max(50, n_results * 5))

    by_id: Dict[str, Dict[str, Any]] = {}
    for r in fts_rows:
        by_id[r["doc_id"]] = {
            "doc_id": r["doc_id"],
            "book_id": r.get("book_id"),
            "chapter_id": r.get("chapter_id"),
            "narrator": r.get("narrator"),
            "english_text": r.get("english_text", ""),
            "fts_bm25": r.get("bm25"),
            "vector_similarity": None,
        }

    # Attach vector scores; backfill text via FTS if missing
    missing_for_fetch: List[str] = []
    for r in emb_rows:
        doc_id = r.get("doc_id")
        if not doc_id:
            continue
        item = by_id.get(doc_id)
        if item is None:
            item = {
                "doc_id": doc_id,
                "book_id": None,
                "chapter_id": None,
                "narrator": None,
                "english_text": "",
                "fts_bm25": None,
                "vector_similarity": r.get("similarity", 0.0),
            }
            by_id[doc_id] = item
            missing_for_fetch.append(doc_id)
        else:
            item["vector_similarity"] = r.get("similarity", 0.0)

    if missing_for_fetch:
        backfill = fts.get_by_doc_ids(missing_for_fetch)
        for doc_id, row in backfill.items():
            item = by_id.get(doc_id)
            if item is not None:
                item.update({
                    "book_id": row.get("book_id"),
                    "chapter_id": row.get("chapter_id"),
                    "narrator": row.get("narrator"),
                    "english_text": row.get("english_text", ""),
                })

    scored = []
    for item in by_id.values():
        bd = scorer.calculate_priority_score(
            intent=intent,
            text=item.get("english_text", ""),
            vector_similarity=item.get("vector_similarity"),
            fts_bm25=item.get("fts_bm25"),
        )
        scored.append({
            "doc_id": item.get("doc_id"),
            "book_id": item.get("book_id"),
            "chapter_id": item.get("chapter_id"),
            "narrator": item.get("narrator"),
            "snippet": (item.get("english_text", "") or "").strip()[:240],
            "score": bd.total,
            "breakdown": serialize_breakdown(bd),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    hits = scored[: int(n_results)]
    return {
        "query": query,
        "intent": intent.type,
        "mode": mode or "balanced",
        "collection": cfg["name"],
        "total_candidates": len(scored),
        "hits": hits,
        "weights": {
            "weight_vector": scorer.weight_vector,
            "weight_fts": scorer.weight_fts,
            "weight_term_coverage": scorer.weight_term_coverage,
            "bonus_phrase": scorer.bonus_phrase,
            "bonus_proximity": scorer.bonus_proximity,
        },
    }


def _resolve_collection_index_config(name: str) -> Dict[str, str]:
    name = (name or "riyadussalihin").lower()
    if name == "riyadussalihin":
        return {
            "name": "riyadussalihin",
            "fts_db": "data/indexes/fts/hadith.db",
            "chroma_dir": "data/indexes/chroma",
            "chroma_collection": "hadith_documents",
        }
    # Default layout for other collections (separate directories)
    base = f"data/indexes/{name}"
    return {
        "name": name,
        "fts_db": f"{base}/fts.db",
        "chroma_dir": f"{base}/chroma",
        "chroma_collection": f"{name}_documents",
    }


__all__ = [
    "vector_index_status",
    "fts_status",
    "hybrid_search",
]
