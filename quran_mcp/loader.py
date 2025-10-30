"""Utilities for loading the Quran tafsir JSONL corpus."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

_P_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(value: str) -> str:
    text = _P_TAG_RE.sub(" ", value)
    text = unescape(text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


@dataclass(frozen=True)
class TafsirEntry:
    """Represents a single tafsir record for a verse."""

    surah: int
    ayah: int
    verse_key: str
    resource_id: int
    resource_name: str
    language_id: int
    slug: Optional[str]
    text_html: str
    text_plain: str
    translated_name: Optional[Dict[str, str]] = None


class QuranCorpus:
    """Loads and caches tafsir entries from JSONL files."""

    def __init__(self, data_dir: Path | str = Path("data/quran")) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Quran data directory not found: {self.data_dir}")
        self._entries: List[TafsirEntry] | None = None
        self._by_key: Dict[str, TafsirEntry] | None = None
        self._manifest: List[Dict[str, object]] | None = None

    @property
    def entries(self) -> List[TafsirEntry]:
        if self._entries is None:
            self._load()
        assert self._entries is not None
        return self._entries

    @property
    def by_key(self) -> Dict[str, TafsirEntry]:
        if self._by_key is None:
            self._load()
        assert self._by_key is not None
        return self._by_key

    def _load(self) -> None:
        entries: List[TafsirEntry] = []
        by_key: Dict[str, TafsirEntry] = {}
        manifest: List[Dict[str, object]] = []
        jsonl_files = sorted(self.data_dir.glob("surah_*.jsonl"))
        if not jsonl_files:
            raise FileNotFoundError(f"No JSONL files found in {self.data_dir}")

        for path in jsonl_files:
            stat = path.stat()
            manifest.append(
                {
                    "name": path.name,
                    "size": stat.st_size,
                    "mtime": round(stat.st_mtime, 3),
                }
            )
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
                    entry = TafsirEntry(
                        surah=int(payload.get("surah")),
                        ayah=int(payload.get("ayah")),
                        verse_key=str(payload.get("verse_key")),
                        resource_id=int(payload.get("resource_id", 0)),
                        resource_name=str(payload.get("resource_name", "")),
                        language_id=int(payload.get("language_id", 0)),
                        slug=payload.get("slug"),
                        text_html=str(payload.get("text_html", "")),
                        text_plain=_strip_html(str(payload.get("text_html", ""))),
                        translated_name=payload.get("translated_name"),
                    )
                    entries.append(entry)
                    by_key[entry.verse_key] = entry
        self._entries = entries
        self._by_key = by_key
        self._manifest = manifest

    def iter_entries(self) -> Iterator[TafsirEntry]:
        yield from self.entries

    def get_by_verse_key(self, verse_key: str) -> Optional[TafsirEntry]:
        return self.by_key.get(verse_key)

    def get(self, surah: int, ayah: int) -> Optional[TafsirEntry]:
        key = f"{int(surah)}:{int(ayah)}"
        return self.get_by_verse_key(key)

    @property
    def manifest(self) -> List[Dict[str, object]]:
        if self._manifest is None:
            self._load()
        assert self._manifest is not None
        return self._manifest


@lru_cache(maxsize=1)
def get_corpus(data_dir: Path | str = Path("data/quran")) -> QuranCorpus:
    """Return a cached corpus instance."""

    return QuranCorpus(data_dir=data_dir)


__all__ = ["TafsirEntry", "QuranCorpus", "get_corpus"]
