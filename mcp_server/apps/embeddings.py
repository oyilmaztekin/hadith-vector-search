"""ChromaDB embedding index helpers."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .models import HadithDocument
from .validation import validate_book

try:  # pragma: no cover - optional dependency check
    import chromadb
    from chromadb.api.models.Collection import Collection
except Exception:  # pragma: no cover - handle missing dependency gracefully
    chromadb = None  # type: ignore[assignment]
    Collection = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency check
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - handle missing dependency gracefully
    SentenceTransformer = None  # type: ignore[assignment]


class EmbeddingDependencyError(RuntimeError):
    """Raised when optional embedding dependencies are unavailable."""


@dataclass
class EmbeddingUpdateResult:
    processed: int
    inserted: int
    skipped: int
    duration_seconds: float


def _document_id(doc: HadithDocument) -> str:
    return f"{doc.collection_slug}:{doc.book_id}:{doc.hadith_id_site}"


def _render_document(doc: HadithDocument) -> str:
    english = next((t.content for t in doc.texts if t.language == "en"), "")
    arabic = next((t.content for t in doc.texts if t.language == "ar"), "")
    narrator = doc.canonical_narrator or (doc.narrator or "")
    header = f"Narrator: {narrator}\n" if narrator else ""
    return f"{header}{english}\n\n{arabic}".strip()


class EmbeddingIndex:
    """Wrapper around a persistent ChromaDB collection with checksum caching."""

    def __init__(
        self,
        persist_directory: Path | str = Path("data/indexes/chroma"),
        collection_name: str = "hadith_documents",
        embedding_model: str = "all-MiniLM-L6-v2",
        checksum_filename: str = "checksums.json",
        metadata_filename: str = "metadata.json",
    ) -> None:
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.checksum_path = self.persist_directory / checksum_filename
        self.metadata_path = self.persist_directory / metadata_filename
        self._checksum_cache: Dict[str, str] = {}
        self._client = None
        self._collection: Optional[Collection] = None
        self._model: Optional[SentenceTransformer] = None  # type: ignore[assignment]
        self._dependency_error: Optional[str] = None

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._load_checksum_cache()
        self._initialise_client()

    # public API -------------------------------------------------
    def dependencies_ok(self) -> bool:
        return self._dependency_error is None

    def status(self) -> Dict[str, object]:
        doc_count: Optional[int] = None
        dimension: Optional[int] = None
        last_updated: Optional[str] = None

        if self.dependencies_ok() and self._collection is not None:
            try:
                doc_count = self._collection.count()
                sample = self._collection.peek(limit=1)
                embeddings = sample.get("embeddings") if sample else None
                if embeddings is not None:
                    try:
                        embedding = embeddings[0]
                        dimension = len(embedding)
                    except Exception:  # pragma: no cover - defensive
                        dimension = None
            except Exception:  # pragma: no cover - defensive
                doc_count = None
                dimension = None

        if self.metadata_path.exists():
            try:
                payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                last_updated = payload.get("last_updated")
            except Exception:  # pragma: no cover - defensive
                last_updated = None

        return {
            "collection": self.collection_name,
            "persist_directory": str(self.persist_directory),
            "document_count": doc_count,
            "cached_documents": len(self._checksum_cache),
            "embedding_dimension": dimension,
            "model": self.embedding_model_name,
            "dependencies_ok": self.dependencies_ok(),
            "dependency_error": self._dependency_error,
            "last_updated": last_updated,
        }

    def upsert_documents(
        self,
        documents: Iterable[HadithDocument],
        force: bool = False,
    ) -> EmbeddingUpdateResult:
        if not self.dependencies_ok() or self._collection is None:
            raise EmbeddingDependencyError(
                self._dependency_error
                or "Embedding dependencies unavailable; install chromadb and sentence-transformers"
            )

        start = time.perf_counter()
        ids: List[str] = []
        payloads: List[str] = []
        metadatas: List[Dict[str, object]] = []
        to_cache: Dict[str, str] = {}
        skipped = 0

        for doc in documents:
            doc_id = _document_id(doc)
            checksum = doc.checksum or ""
            if not force and checksum and self._checksum_cache.get(doc_id) == checksum:
                skipped += 1
                continue

            ids.append(doc_id)
            payloads.append(_render_document(doc))
            metadatas.append(
                {
                    "collection_slug": doc.collection_slug,
                    "book_id": doc.book_id,
                    "chapter_id": doc.chapter_id,
                    "hadith_id_site": doc.hadith_id_site,
                    "narrator": doc.canonical_narrator or doc.narrator,
                    "checksum": checksum,
                }
            )
            if checksum:
                to_cache[doc_id] = checksum

        if not ids:
            duration = time.perf_counter() - start
            return EmbeddingUpdateResult(
                processed=skipped,
                inserted=0,
                skipped=skipped,
                duration_seconds=duration,
            )

        embeddings = self._encode(payloads)
        self._collection.upsert(
            ids=ids,
            documents=payloads,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        self._checksum_cache.update(to_cache)
        self._save_checksum_cache()
        self._write_metadata()

        duration = time.perf_counter() - start
        return EmbeddingUpdateResult(
            processed=skipped + len(ids),
            inserted=len(ids),
            skipped=skipped,
            duration_seconds=duration,
        )

    def upsert_books(
        self,
        data_dir: Path | str = Path("data/riyadussalihin"),
        book_ids: Iterable[str] | None = None,
        force: bool = False,
    ) -> EmbeddingUpdateResult:
        start = time.perf_counter()
        total_processed = 0
        total_inserted = 0
        total_skipped = 0

        data_path = Path(data_dir)
        for path in _resolve_book_paths(data_path, book_ids):
            records, _ = validate_book(path)
            result = self.upsert_documents(records, force=force)
            total_processed += result.processed
            total_inserted += result.inserted
            total_skipped += result.skipped

        duration = time.perf_counter() - start
        return EmbeddingUpdateResult(
            processed=total_processed,
            inserted=total_inserted,
            skipped=total_skipped,
            duration_seconds=duration,
        )

    # internal helpers ------------------------------------------
    def _initialise_client(self) -> None:
        if chromadb is None:
            self._dependency_error = "chromadb is not installed"
            return

        try:
            self._client = chromadb.PersistentClient(path=str(self.persist_directory))
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._dependency_error = f"Failed to initialise ChromaDB client: {exc}"

    def _load_checksum_cache(self) -> None:
        if self.checksum_path.exists():
            try:
                self._checksum_cache = json.loads(
                    self.checksum_path.read_text(encoding="utf-8")
                )
            except Exception:  # pragma: no cover - defensive
                self._checksum_cache = {}

    def _save_checksum_cache(self) -> None:
        self.checksum_path.write_text(
            json.dumps(self._checksum_cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_metadata(self) -> None:
        payload = {
            "model": self.embedding_model_name,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        self.metadata_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _encode(self, payloads: List[str]) -> List[List[float]]:
        model = self._ensure_model()
        # Convert to plain lists to avoid dependency on numpy exporting
        vectors = model.encode(payloads, convert_to_numpy=True)
        return [vector.tolist() for vector in vectors]

    def _ensure_model(self) -> SentenceTransformer:
        if SentenceTransformer is None:
            raise EmbeddingDependencyError(
                "sentence-transformers is not installed; install to generate embeddings"
            )
        if self._model is None:
            try:
                self._model = SentenceTransformer(self.embedding_model_name)
            except Exception as exc:  # pragma: no cover - defensive
                raise EmbeddingDependencyError(
                    f"Failed to load embedding model '{self.embedding_model_name}': {exc}"
                ) from exc
        return self._model

    def query(self, query_text: str, n_results: int = 20) -> List[Dict[str, object]]:
        """Return top-N vector candidates with normalized similarity.

        Uses local SentenceTransformer to embed the query and queries Chroma with
        query_embeddings to avoid relying on collection-level embedding functions.
        Converts distances to a [0,1] similarity via 1 / (1 + distance), which is
        robust for cosine distances that may exceed 1.0.
        """
        if not self.dependencies_ok() or self._collection is None:
            return []
        try:
            # Embed query locally for consistent scoring with upserted vectors
            model = self._ensure_model()
            qvec = model.encode([query_text], convert_to_numpy=True)
            res = self._collection.query(
                query_embeddings=qvec.tolist(),
                n_results=int(n_results),
                include=["distances", "metadatas"],
            )
            ids = res.get("ids", [[]])[0]
            distances = res.get("distances", [[]])[0]
            metadatas = res.get("metadatas", [[]])[0]
            out: List[Dict[str, object]] = []
            for i, doc_id in enumerate(ids or []):
                dist = None
                if distances and i < len(distances):
                    d = distances[i]
                    try:
                        dist = float(d) if d is not None else None
                    except Exception:
                        dist = None
                sim = 0.0
                if dist is not None:
                    # Normalize distance to similarity in [0,1]
                    sim = 1.0 / (1.0 + max(0.0, dist))
                md = metadatas[i] if metadatas and i < len(metadatas) else {}
                out.append({
                    "doc_id": doc_id,
                    "similarity": sim,
                    "distance": dist,
                    "metadata": md or {},
                })
            return out
        except Exception:
            return []


__all__ = [
    "EmbeddingIndex",
    "EmbeddingUpdateResult",
    "EmbeddingDependencyError",
]


def _resolve_book_paths(
    data_dir: Path,
    book_ids: Iterable[str] | None = None,
) -> List[Path]:
    if book_ids is None:
        paths = sorted(data_dir.glob("book_*.jsonl"))
        intro = data_dir / "book_introduction.jsonl"
        if intro.exists():
            paths.insert(0, intro)
        return paths

    resolved: List[Path] = []
    for bid in book_ids:
        file_name = "book_introduction.jsonl" if bid == "introduction" else f"book_{bid}.jsonl"
        path = data_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Book file not found: {path}")
        resolved.append(path)
    return resolved
