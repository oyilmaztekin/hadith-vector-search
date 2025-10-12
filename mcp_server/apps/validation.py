"""Validation utilities for hadith ingestion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Tuple

from pydantic import ValidationError

from .models import HadithDocument, BookStats


class ValidationIssue(Exception):
    """Raised when validation failures exceed acceptable thresholds."""


def load_hadith_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield line


def validate_book(path: Path, max_errors: int = 10) -> Tuple[List[HadithDocument], BookStats]:
    records: List[HadithDocument] = []
    warnings: List[str] = []
    errors = 0
    narrators = set()
    checksums = []

    for raw in load_hadith_lines(path):
        try:
            data = json.loads(raw)
            doc = HadithDocument.parse_obj(data)
            records.append(doc)
            if doc.canonical_narrator:
                narrators.add(doc.canonical_narrator)
            if doc.checksum:
                checksums.append(doc.checksum)
        except (json.JSONDecodeError, ValidationError) as exc:  # type: ignore[arg-type]
            errors += 1
            warnings.append(f"Validation error: {exc}")
            if errors >= max_errors:
                raise ValidationIssue(
                    f"Validation halted after {errors} errors in {path}"
                ) from exc

    stats = BookStats(
        book_id=path.stem.replace("book_", ""),
        total_hadith=len(records),
        unique_narrators=len(narrators),
        checksum_examples=checksums[:5],
        warnings=warnings,
    )
    return records, stats


__all__ = ["validate_book", "ValidationIssue"]
