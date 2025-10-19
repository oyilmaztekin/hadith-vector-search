"""SQLite FTS5 index helpers for hadith search."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional
from .models import HadithDocument
from .validation import validate_book


class FtsIndexError(RuntimeError):
    """Raised when the underlying SQLite database cannot support FTS features."""


@dataclass
class FtsUpdateResult:
    processed: int
    inserted: int
    skipped: int
    duration_seconds: float


def _document_id(doc: HadithDocument) -> str:
    return f"{doc.collection_slug}:{doc.book_id}:{doc.hadith_id_site}"


def _english_text(doc: HadithDocument) -> str:
    return next((t.content for t in doc.texts if t.language == "en"), "")


def _arabic_text(doc: HadithDocument) -> str:
    return next((t.content for t in doc.texts if t.language == "ar"), "")


class FTSIndex:
    """Manage the SQLite FTS5 index for hadith documents."""

    def __init__(
        self,
        db_path: Path | str = Path("data/indexes/fts/hadith.db"),
        metadata_filename: str = "metadata.json",
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.db_path.parent / metadata_filename
        self._dependency_error: Optional[str] = None
        self._initialise()

    # public API -------------------------------------------------
    def dependencies_ok(self) -> bool:
        return self._dependency_error is None

    def status(self) -> Dict[str, object]:
        document_count: Optional[int] = None
        sample: List[Dict[str, object]] = []
        last_updated: Optional[str] = None

        if self.metadata_path.exists():
            try:
                payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                last_updated = payload.get("last_updated")
            except Exception:  # pragma: no cover - defensive
                last_updated = None

        if self.dependencies_ok():
            try:
                with self._connect() as conn:
                    document_count = conn.execute(
                        "SELECT COUNT(*) FROM documents"
                    ).fetchone()[0]
                    rows = conn.execute(
                        "SELECT doc_id, book_id, narrator, substr(english_text, 1, 120) AS snippet "
                        "FROM hadith_fts LIMIT 3"
                    ).fetchall()
                    sample = [dict(row) for row in rows]
            except Exception:  # pragma: no cover - defensive
                document_count = None
                sample = []

        return {
            "db_path": str(self.db_path),
            "dependencies_ok": self.dependencies_ok(),
            "dependency_error": self._dependency_error,
            "document_count": document_count,
            "sample": sample,
            "last_updated": last_updated,
        }

    def search_match(self, match: str, limit: int = 20) -> List[Dict[str, object]]:
        if not self.dependencies_ok():
            raise FtsIndexError(self._dependency_error or "FTS unavailable")
        sql = (
            "SELECT doc_id, book_id, chapter_id, narrator, english_text, bm25(hadith_fts) AS bm25 "
            "FROM hadith_fts WHERE hadith_fts MATCH ? ORDER BY bm25 LIMIT ?"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, (match, int(limit))).fetchall()
            return [dict(row) for row in rows]

    def get_by_doc_ids(self, ids: List[str]) -> Dict[str, Dict[str, object]]:
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        sql = (
            f"SELECT doc_id, book_id, chapter_id, narrator, english_text FROM hadith_fts "
            f"WHERE doc_id IN ({placeholders})"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, ids).fetchall()
            return {row["doc_id"]: dict(row) for row in rows}

    def upsert_documents(
        self,
        documents: Iterable[HadithDocument],
        force: bool = False,
    ) -> FtsUpdateResult:
        if not self.dependencies_ok():
            raise FtsIndexError(
                self._dependency_error
                or "SQLite build lacks FTS5 support; unable to update index"
            )

        start = time.perf_counter()
        docs = list(documents)
        if not docs:
            return FtsUpdateResult(processed=0, inserted=0, skipped=0, duration_seconds=0.0)

        ids = [_document_id(doc) for doc in docs]
        checksums = {doc_id: doc.checksum or "" for doc_id, doc in zip(ids, docs)}
        skipped = 0
        inserted = 0

        with self._connect() as conn:
            existing = self._fetch_existing_checksums(conn, ids)
            for doc_id, doc in zip(ids, docs):
                checksum = checksums[doc_id]
                if not force and checksum and existing.get(doc_id) == checksum:
                    skipped += 1
                    continue

                english_text = _english_text(doc)
                arabic_text = _arabic_text(doc)
                narrator = doc.canonical_narrator or doc.narrator or ""
                conn.execute(
                    "INSERT INTO documents (doc_id, collection_slug, book_id, chapter_id, narrator, checksum) "
                    "VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(doc_id) DO UPDATE SET "
                    "collection_slug=excluded.collection_slug, "
                    "book_id=excluded.book_id, "
                    "chapter_id=excluded.chapter_id, "
                    "narrator=excluded.narrator, "
                    "checksum=excluded.checksum",
                    (
                        doc_id,
                        doc.collection_slug,
                        doc.book_id,
                        doc.chapter_id,
                        narrator,
                        checksum,
                    ),
                )
                conn.execute("DELETE FROM hadith_fts WHERE doc_id = ?", (doc_id,))
                conn.execute(
                    "INSERT INTO hadith_fts (doc_id, english_text, arabic_text, narrator, book_id, chapter_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        doc_id,
                        english_text,
                        arabic_text,
                        narrator,
                        doc.book_id,
                        doc.chapter_id,
                    ),
                )
                inserted += 1

        if inserted:
            self._write_metadata()

        duration = time.perf_counter() - start
        processed = len(docs)
        return FtsUpdateResult(
            processed=processed,
            inserted=inserted,
            skipped=skipped,
            duration_seconds=duration,
        )

    def seed_sample_book(self, book_id: str = "1", force: bool = False) -> FtsUpdateResult:
        paths = _resolve_book_paths(Path("data/riyadussalihin"), [book_id])
        if not paths:
            return FtsUpdateResult(processed=0, inserted=0, skipped=0, duration_seconds=0.0)
        records, _ = validate_book(paths[0])
        return self.upsert_documents(records, force=force)

    def seed_books(
        self,
        data_dir: Path | str = Path("data/riyadussalihin"),
        book_ids: Iterable[str] | None = None,
        force: bool = False,
    ) -> FtsUpdateResult:
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
        return FtsUpdateResult(
            processed=total_processed,
            inserted=total_inserted,
            skipped=total_skipped,
            duration_seconds=duration,
        )

    # internal helpers ------------------------------------------
    def _initialise(self) -> None:
        try:
            with self._connect() as conn:
                self._ensure_fts5(conn)
                self._create_tables(conn)
        except FtsIndexError as exc:
            self._dependency_error = str(exc)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        finally:  # pragma: no cover - connection cleanup
            conn.close()

    def _ensure_fts5(self, conn: sqlite3.Connection) -> None:
        try:
            options = {row[0] for row in conn.execute("PRAGMA compile_options")}
        except sqlite3.DatabaseError:  # pragma: no cover - fallback path
            options = set()

        if "ENABLE_FTS5" in options:
            return

        try:  # attempt to create a throwaway FTS5 table
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS __fts5_probe USING fts5(x)")
            conn.execute("DROP TABLE IF EXISTS __fts5_probe")
        except sqlite3.DatabaseError as exc:
            raise FtsIndexError("SQLite build lacks FTS5 support") from exc

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS documents ("
            "doc_id TEXT PRIMARY KEY,"
            "collection_slug TEXT,"
            "book_id TEXT,"
            "chapter_id TEXT,"
            "narrator TEXT,"
            "checksum TEXT"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS metadata ("
            "key TEXT PRIMARY KEY,"
            "value TEXT NOT NULL"
            ")"
        )
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS hadith_fts USING fts5("
            "doc_id UNINDEXED,"
            "english_text,"
            "arabic_text,"
            "narrator,"
            "book_id,"
            "chapter_id,"
            "tokenize = 'unicode61'"
            ")"
        )

    def _fetch_existing_checksums(
        self, conn: sqlite3.Connection, ids: List[str]
    ) -> Dict[str, str]:
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT doc_id, checksum FROM documents WHERE doc_id IN ({placeholders})",
            ids,
        ).fetchall()
        return {row["doc_id"]: row["checksum"] or "" for row in rows}

    def _write_metadata(self) -> None:
        payload = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "db_path": str(self.db_path),
        }
        self.metadata_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


__all__ = ["FTSIndex", "FtsUpdateResult", "FtsIndexError"]


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
