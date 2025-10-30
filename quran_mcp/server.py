"""FastMCP server definition for Quran tafsir tools."""

from __future__ import annotations

import os
from typing import Optional

from fastmcp.server import FastMCP

from .search import QuranSearchIndex

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_STREAM_PATH = "/mcp"


def _resolve_host(host: str | None) -> str:
    return host or os.getenv("QURAN_MCP_HOST") or DEFAULT_HOST


def _resolve_port(port: int | None) -> int:
    if port is not None:
        return port

    env_port = os.getenv("QURAN_MCP_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise ValueError(f"Invalid QURAN_MCP_PORT value: {env_port!r}") from exc

    return DEFAULT_PORT


def _resolve_path(path: str | None) -> str:
    return path or os.getenv("QURAN_MCP_PATH") or DEFAULT_STREAM_PATH


def create_server(
    *,
    host: str | None = None,
    port: int | None = None,
    stream_path: str | None = None,
) -> FastMCP:
    """Instantiate and configure the Quran tafsir MCP server."""

    server = FastMCP(
        name="quran-tafsir",
        host=_resolve_host(host),
        port=_resolve_port(port),
        streamable_http_path=_resolve_path(stream_path),
    )
    index = QuranSearchIndex()

    @server.tool(
        description="Hybrid (BM25 + semantic) search over the Ibn Kathir (Abridged) tafsir",
    )
    def search_tafsir(
        query: str,
        limit: int = 5,
        mode: str = "hybrid",
        weight_vector: Optional[float] = None,
        weight_fts: Optional[float] = None,
        dedupe: bool = True,
    ) -> dict:
        """Return ranked tafsir passages for the supplied query."""

        return index.search(
            query,
            limit=limit,
            mode=mode,
            weight_vector=weight_vector,
            weight_fts=weight_fts,
            dedupe=dedupe,
        )

    @server.tool(description="Fetch tafsir entry by verse key or (surah, ayah)")
    def get_verse(
        verse_key: Optional[str] = None,
        surah: Optional[int] = None,
        ayah: Optional[int] = None,
    ) -> dict:
        """Return tafsir for a specific verse."""

        entry = None
        if verse_key:
            entry = index.get(verse_key)
        elif surah is not None and ayah is not None:
            entry = index.get_by_surah(int(surah), int(ayah))

        if not entry:
            return {
                "error": "Verse not found",
                "input": {
                    "verse_key": verse_key,
                    "surah": surah,
                    "ayah": ayah,
                },
            }

        return {
            "verse_key": entry.verse_key,
            "surah": entry.surah,
            "ayah": entry.ayah,
            "resource": entry.resource_name,
            "text_html": entry.text_html,
            "text_plain": entry.text_plain,
        }

    @server.tool(description="Return status information about the tafsir index")
    def index_status() -> dict:
        """Return FTS/vector index stats."""

        return index.status()

    return server


__all__ = ["create_server", "DEFAULT_HOST", "DEFAULT_PORT", "DEFAULT_STREAM_PATH"]
