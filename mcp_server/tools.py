"""High-level MCP tool functions for index status reporting."""

from __future__ import annotations

from typing import Any, Dict

from .apps.embeddings import EmbeddingIndex
from .apps.fts import FTSIndex


def vector_index_status() -> Dict[str, Any]:
    """Return status information about the embedding (vector) index."""

    index = EmbeddingIndex()
    return index.status()


def fts_status() -> Dict[str, Any]:
    """Return status information about the SQLite FTS index."""

    index = FTSIndex()
    return index.status()


__all__ = ["vector_index_status", "fts_status"]

