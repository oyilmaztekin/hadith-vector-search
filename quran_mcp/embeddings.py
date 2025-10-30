"""Embedding utilities for the Quran tafsir corpus."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from .loader import QuranCorpus, TafsirEntry

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_INDEX_DIR = Path("data/indexes/quran")
_CACHE_FILENAME = "embeddings.npz"
_METADATA_FILENAME = "metadata.json"


@lru_cache(maxsize=2)
def get_encoder(model_name: str = DEFAULT_MODEL_NAME) -> SentenceTransformer:
    """Return a cached sentence-transformers encoder."""

    return SentenceTransformer(model_name)


def _encode_texts(texts: Iterable[str], model_name: str) -> np.ndarray:
    encoder = get_encoder(model_name)
    vectors = encoder.encode(
        list(texts),
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vectors.astype(np.float32)


def _metadata_path(index_dir: Path) -> Path:
    return index_dir / _METADATA_FILENAME


def _cache_path(index_dir: Path) -> Path:
    return index_dir / _CACHE_FILENAME


def _metadata_matches(existing: dict, model_name: str, corpus: QuranCorpus) -> bool:
    if not existing:
        return False
    if existing.get("model_name") != model_name:
        return False
    if int(existing.get("entry_count", -1)) != len(corpus.entries):
        return False
    if existing.get("manifest") != corpus.manifest:
        return False
    return True


def load_or_build_embeddings(
    corpus: QuranCorpus,
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    index_dir: Path | str = _INDEX_DIR,
) -> Tuple[np.ndarray, List[str]]:
    """Load cached embeddings or build them if cache is missing/outdated."""

    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    meta_path = _metadata_path(index_dir)
    cache_path = _cache_path(index_dir)

    metadata = {}
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text())
        except Exception:
            metadata = {}

    if cache_path.exists() and _metadata_matches(metadata, model_name, corpus):
        with np.load(cache_path, allow_pickle=True) as data:
            vectors = data["vectors"]
            keys = data["keys"].tolist()
        return vectors.astype(np.float32), list(keys)

    entries = corpus.entries
    texts = [entry.text_plain for entry in entries]
    keys = [entry.verse_key for entry in entries]
    vectors = _encode_texts(texts, model_name=model_name)

    np.savez_compressed(cache_path, vectors=vectors, keys=np.array(keys))
    new_metadata = {
        "model_name": model_name,
        "entry_count": len(entries),
        "manifest": corpus.manifest,
    }
    meta_path.write_text(json.dumps(new_metadata, indent=2))
    return vectors, keys


def encode_query(query: str, *, model_name: str = DEFAULT_MODEL_NAME) -> np.ndarray:
    """Encode a single query string into a normalized embedding."""

    if not query:
        raise ValueError("Query text must be non-empty for embedding")
    vector = _encode_texts([query], model_name=model_name)[0]
    return vector


__all__ = [
    "DEFAULT_MODEL_NAME",
    "encode_query",
    "get_encoder",
    "load_or_build_embeddings",
]
