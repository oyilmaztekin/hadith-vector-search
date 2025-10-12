"""Normalization helpers for narrators and textual metadata."""

from __future__ import annotations

import re
from typing import Optional

HONORIFICS_PATTERN = re.compile(
    r"\((?:may|may allah be pleased|رضي الله عن(?:ه|ها|هم))[^)]*\)", re.IGNORECASE
)
VERB_PATTERN = re.compile(r"\b(reported|narrated|said|stated)\b:?", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")


def extract_narrator_name(raw: Optional[str]) -> Optional[str]:
    """Return a canonical narrator name stripped of honorifics and verbs."""
    if not raw:
        return None
    # Remove honorific parentheticals
    cleaned = HONORIFICS_PATTERN.sub("", raw)
    # Remove reporting verbs at start/end
    cleaned = VERB_PATTERN.sub("", cleaned)
    # Strip punctuation artifacts
    cleaned = cleaned.replace(":", "").replace("،", "")
    cleaned = WHITESPACE_PATTERN.sub(" ", cleaned)
    return cleaned.strip(" -\u200f\u200e\ufeff") or None


__all__ = ["extract_narrator_name"]
