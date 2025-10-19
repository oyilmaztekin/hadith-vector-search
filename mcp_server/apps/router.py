"""Query router heuristics for hybrid search."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .normalization import extract_narrator_name


class QueryType:
    EXACT_REFERENCE = "exact_reference"
    NARRATOR = "narrator"
    THEMATIC = "thematic"
    MIXED = "mixed"


NARRATED_PAT = re.compile(r"\b(narrated by|reported by|said by)\b\s*(.+)$", re.IGNORECASE)
AR_NARRATOR_PAT = re.compile(r"\bعن\s+(.+)$")
EXACT_REF_PAT = re.compile(r"\b(?:book|kitab|bk)?\s*\d+(?:\s*[:\-/]\s*\d+)?\b", re.IGNORECASE)


def _strip_quotes(q: str) -> str:
    q = q.strip()
    if (q.startswith('"') and q.endswith('"')) or (q.startswith("'") and q.endswith("'")):
        return q[1:-1].strip()
    return q


def _first_quoted_phrase(q: str) -> Optional[str]:
    m = re.search(r'"([^"]{3,})"', q)
    if m:
        return m.group(1)
    m = re.search(r"'([^']{3,})'", q)
    if m:
        return m.group(1)
    return None


def _tokenize(q: str) -> List[str]:
    q = q.lower()
    tokens = re.findall(r"[\w\u0600-\u06FF]+", q)
    return [t for t in tokens if len(t) > 1]


@dataclass
class QueryIntent:
    type: str
    raw: str
    normalized: str
    narrator_query: Optional[str] = None
    phrase: Optional[str] = None
    tokens: List[str] = None  # type: ignore[assignment]


def route_query(query: str) -> QueryIntent:
    q = query.strip()
    phrase = _first_quoted_phrase(q)
    narr = None

    m = NARRATED_PAT.search(q)
    if m:
        narr = extract_narrator_name(m.group(2)) or m.group(2).strip()

    if narr is None:
        m_ar = AR_NARRATOR_PAT.search(q)
        if m_ar:
            narr = extract_narrator_name(m_ar.group(1)) or m_ar.group(1).strip()

    if EXACT_REF_PAT.search(q):
        qtype = QueryType.EXACT_REFERENCE
    elif narr:
        qtype = QueryType.NARRATOR
    else:
        toks = _tokenize(q)
        if len(toks) >= 4 or phrase:
            qtype = QueryType.THEMATIC
        else:
            qtype = QueryType.MIXED

    normalized = _strip_quotes(q)
    return QueryIntent(
        type=qtype,
        raw=query,
        normalized=normalized,
        narrator_query=narr,
        phrase=phrase,
        tokens=_tokenize(normalized),
    )


def build_fts_match(intent: QueryIntent) -> str:
    if intent.type == QueryType.NARRATOR and intent.narrator_query:
        toks = _tokenize(intent.narrator_query)
        if not toks:
            toks = intent.tokens
        parts = [f"narrator:{t}*" for t in toks[:6]]
        return " AND ".join(parts) if parts else intent.normalized

    if intent.phrase and len(intent.phrase) >= 3:
        return f'"{intent.phrase}"'

    toks = intent.tokens[:6]
    if not toks:
        return intent.normalized
    return " AND ".join(f"{t}*" for t in toks)


__all__ = ["QueryType", "QueryIntent", "route_query", "build_fts_match"]

