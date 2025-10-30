"""Hybrid FTS + vector search over the Quran tafsir corpus."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .loader import QuranCorpus, TafsirEntry, get_corpus
from .embeddings import (
    DEFAULT_MODEL_NAME,
    encode_query,
    load_or_build_embeddings,
)


@dataclass
class SearchHit:
    verse_key: str
    surah: int
    ayah: int
    score: float
    snippet: str
    text_plain: str


class QuranSearchIndex:
    """Hybrid search index supporting BM25 FTS and semantic similarity."""

    def __init__(self, corpus: QuranCorpus | None = None) -> None:
        if corpus is None:
            data_dir = os.environ.get("QURAN_MCP_DATA_DIR")
            corpus = get_corpus(Path(data_dir)) if data_dir else get_corpus()
        self.corpus = corpus
        self._conn: Optional[sqlite3.Connection] = None
        self._loaded: bool = False
        self._vectors: Optional[np.ndarray] = None
        self._vector_keys: Optional[List[str]] = None
        self._model_name: str = os.environ.get("QURAN_MCP_MODEL", DEFAULT_MODEL_NAME)
        self._vector_error: Optional[str] = None

    def _ensure_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(":memory:")
            conn.execute("PRAGMA journal_mode=OFF")
            conn.row_factory = sqlite3.Row
            self._conn = conn
        return self._conn

    def _ensure_index(self) -> None:
        if self._loaded:
            return
        conn = self._ensure_connection()
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS tafsir USING fts5("
            "verse_key UNINDEXED,"
            "surah UNINDEXED,"
            "ayah UNINDEXED,"
            "content"
            ")"
        )
        with conn:
            for entry in self.corpus.iter_entries():
                conn.execute(
                    "INSERT INTO tafsir (verse_key, surah, ayah, content) VALUES (?, ?, ?, ?)",
                    (entry.verse_key, entry.surah, entry.ayah, entry.text_plain),
                )
        self._loaded = True

    def _ensure_vectors(self) -> None:
        if self._vectors is not None and self._vector_keys is not None:
            return
        if self._vector_error is not None:
            return
        if self._vectors is not None and self._vector_keys is not None:
            return
        try:
            vectors, keys = load_or_build_embeddings(
                self.corpus,
                model_name=self._model_name,
            )
        except Exception as exc:  # pragma: no cover - network / model failures
            self._vector_error = str(exc)
            self._vectors = None
            self._vector_keys = None
            return
        self._vectors = vectors
        self._vector_keys = keys

    def status(self) -> Dict[str, object]:
        self._ensure_index()
        assert self._conn is not None
        row = self._conn.execute("SELECT COUNT(*) AS n FROM tafsir").fetchone()
        vector_count = None
        if self._vectors is not None:
            vector_count = int(self._vectors.shape[0])
        return {
            "entries": int(row["n"] if row is not None else 0),
            "surah_count": len({e.surah for e in self.corpus.entries}),
            "loaded": self._loaded,
            "vector_model": self._model_name,
            "vector_count": vector_count,
            "vector_error": self._vector_error,
        }

    def get(self, verse_key: str) -> Optional[TafsirEntry]:
        return self.corpus.get_by_verse_key(verse_key)

    def get_by_surah(self, surah: int, ayah: int) -> Optional[TafsirEntry]:
        return self.corpus.get(surah, ayah)

    def _fts_search(self, query: str, limit: int) -> Tuple[List[Dict[str, object]], Optional[str]]:
        conn = self._ensure_connection()
        try:
            rows = conn.execute(
                "SELECT verse_key, surah, ayah, bm25(tafsir) AS rank, "
                "snippet(tafsir, 3, '[', ']', ' … ', 32) AS snippet "
                "FROM tafsir WHERE tafsir MATCH ? ORDER BY rank LIMIT ?",
                (query, int(limit)),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            return [], str(exc)

        hits: List[Dict[str, object]] = []
        for row in rows:
            verse_key = row["verse_key"]
            entry = self.corpus.get_by_verse_key(verse_key)
            if entry is None:
                continue
            rank = float(row["rank"])
            score = 1.0 / (1.0 + max(rank, 0.0))
            hits.append(
                {
                    "verse_key": verse_key,
                    "score": float(score),
                    "snippet": row["snippet"],
                }
            )
        return hits, None

    def _semantic_search(self, query: str, limit: int) -> Tuple[List[Dict[str, object]], Optional[str]]:
        if limit <= 0:
            return [], None
        self._ensure_vectors()
        if self._vector_error is not None:
            return [], self._vector_error
        if self._vectors is None or self._vector_keys is None:
            return [], "Vector index unavailable"
        try:
            query_vec = encode_query(query, model_name=self._model_name)
        except Exception as exc:  # pragma: no cover - defensive
            return [], str(exc)

        scores = np.dot(self._vectors, query_vec)
        if not np.isfinite(scores).all():
            scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
        top_k = min(limit, scores.shape[0])
        if top_k <= 0:
            return [], None
        top_indices = np.argsort(scores)[-top_k:][::-1]
        hits: List[Dict[str, object]] = []
        for idx in top_indices:
            sim = float(scores[idx])
            if sim <= 0:
                continue
            hits.append(
                {
                    "verse_key": self._vector_keys[idx],
                    "score": sim,
                }
            )
        return hits, None

    def search(
        self,
        query: str,
        limit: int = 5,
        *,
        mode: str = "hybrid",
        weight_vector: Optional[float] = None,
        weight_fts: Optional[float] = None,
    ) -> Dict[str, object]:
        self._ensure_index()
        query = (query or "").strip()
        if not query:
            return {"query": query, "hits": [], "error": "Empty query"}

        mode = (mode or "hybrid").lower()
        presets = {
            "hybrid": (0.6, 0.4),
            "semantic": (1.0, 0.0),
            "vector": (1.0, 0.0),
            "fts": (0.0, 1.0),
        }
        base = presets.get(mode, presets["hybrid"])
        vec_weight = weight_vector if weight_vector is not None else base[0]
        fts_weight = weight_fts if weight_fts is not None else base[1]
        if vec_weight == 0 and fts_weight == 0:
            vec_weight = 1.0

        fts_limit = max(limit * 5, 25)
        fts_hits, fts_error = self._fts_search(query, fts_limit if fts_weight > 0 else limit)
        semantic_hits: List[Dict[str, object]] = []
        semantic_error: Optional[str] = None
        if vec_weight > 0:
            semantic_hits, semantic_error = self._semantic_search(query, max(limit * 5, 50))
            if semantic_error:
                vec_weight = 0.0
                if fts_weight == 0.0:
                    fts_weight = 1.0

        combined: Dict[str, Dict[str, object]] = {}
        for hit in fts_hits:
            verse_key = hit["verse_key"]
            entry = self.corpus.get_by_verse_key(verse_key)
            if entry is None:
                continue
            combined[verse_key] = {
                "verse_key": verse_key,
                "surah": entry.surah,
                "ayah": entry.ayah,
                "resource": entry.resource_name,
                "snippet": hit.get("snippet") or entry.text_plain[:200],
                "text_preview": entry.text_plain[:400],
                "fts_score": hit.get("score", 0.0),
                "vector_score": 0.0,
            }

        for hit in semantic_hits:
            verse_key = hit["verse_key"]
            entry = self.corpus.get_by_verse_key(verse_key)
            if entry is None:
                continue
            item = combined.get(verse_key)
            if item is None:
                item = {
                    "verse_key": verse_key,
                    "surah": entry.surah,
                    "ayah": entry.ayah,
                    "resource": entry.resource_name,
                    "snippet": entry.text_plain[:200],
                    "text_preview": entry.text_plain[:400],
                    "fts_score": 0.0,
                    "vector_score": 0.0,
                }
                combined[verse_key] = item
            item["vector_score"] = max(item.get("vector_score", 0.0), hit.get("score", 0.0))

        for item in combined.values():
            total = vec_weight * item.get("vector_score", 0.0) + fts_weight * item.get("fts_score", 0.0)
            item["score"] = round(float(total), 6)

        hits = sorted(combined.values(), key=lambda x: x.get("score", 0.0), reverse=True)[: int(limit)]

        result = {
            "query": query,
            "mode": mode,
            "limit": limit,
            "hits": [
                {
                    "verse_key": item["verse_key"],
                    "surah": item["surah"],
                    "ayah": item["ayah"],
                    "resource": item["resource"],
                    "snippet": item["snippet"],
                    "score": item["score"],
                    "scores": {
                        "vector": round(float(item.get("vector_score", 0.0)), 6),
                        "fts": round(float(item.get("fts_score", 0.0)), 6),
                    },
                }
                for item in hits
            ],
            "weights": {
                "weight_vector": vec_weight,
                "weight_fts": fts_weight,
            },
            "vector_available": self._vector_error is None and self._vectors is not None,
        }
        errors = {}
        if fts_error:
            errors["fts"] = fts_error
        if semantic_error:
            errors["semantic"] = semantic_error
        if errors:
            result["errors"] = errors
        if self._vector_error is not None:
            result["vector_error"] = self._vector_error
        result["total_candidates"] = len(combined)
        return result


__all__ = ["QuranSearchIndex", "SearchHit"]
