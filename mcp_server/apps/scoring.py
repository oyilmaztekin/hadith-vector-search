"""Hybrid scoring and re-ranking utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, List

from .router import QueryIntent, QueryType


@dataclass
class ScoreBreakdown:
    vector_similarity: float
    fts_signal: float
    phrase_bonus: float
    proximity_bonus: float
    term_coverage: float
    total: float


class HybridScorer:
    def __init__(
        self,
        weight_vector: float = 0.6,
        weight_fts: float = 0.4,
        bonus_phrase: float = 0.05,
        bonus_proximity: float = 0.10,
        weight_term_coverage: float = 0.20,
    ) -> None:
        self.weight_vector = weight_vector
        self.weight_fts = weight_fts
        self.bonus_phrase = bonus_phrase
        self.bonus_proximity = bonus_proximity
        self.weight_term_coverage = weight_term_coverage

    def calculate_priority_score(
        self,
        intent: QueryIntent,
        text: str,
        vector_similarity: Optional[float],
        fts_bm25: Optional[float],
        *,
        synonym_groups: Optional[List[List[str]]] = None,
        near_window: int = 5,
    ) -> ScoreBreakdown:
        v = max(0.0, min(1.0, vector_similarity or 0.0))
        # Convert bm25 (lower is better) into [0,1] signal
        fts_signal = 0.0
        if fts_bm25 is not None:
            fts_signal = 1.0 / (1.0 + max(0.0, fts_bm25))
        fts_signal = max(0.0, min(1.0, fts_signal))

        phrase_bonus = 0.0
        if intent.phrase and intent.phrase.lower() in text.lower():
            phrase_bonus = self.bonus_phrase

        # Term coverage over synonym groups if provided; else fall back to tokens
        coverage = 0.0
        t = text.lower()
        if synonym_groups:
            total_groups = len(synonym_groups)
            if total_groups > 0:
                hits = 0
                for group in synonym_groups:
                    if any(tok.lower() in t for tok in group):
                        hits += 1
                coverage = hits / float(total_groups)
        elif intent.tokens:
            hits = sum(1 for tok in intent.tokens if tok in t)
            coverage = hits / float(len(intent.tokens))

        # Proximity bonus: if at least two groups exist, check near-window proximity
        proximity_bonus = 0.0
        if synonym_groups and len(synonym_groups) >= 2:
            tokens = [w for w in _simple_tokenize(t)]
            # Build indices for first two groups only (verb-group, family-group)
            g0 = set(w.lower() for w in synonym_groups[0])
            g1 = set(w.lower() for w in synonym_groups[1])
            pos_g0 = [i for i, w in enumerate(tokens) if w in g0]
            pos_g1 = [i for i, w in enumerate(tokens) if w in g1]
            if pos_g0 and pos_g1:
                # Check minimal distance
                j = 0
                found_near = False
                for i in pos_g0:
                    # advance j to keep pos_g1[j] close to i
                    while j + 1 < len(pos_g1) and abs(pos_g1[j + 1] - i) <= abs(pos_g1[j] - i):
                        j += 1
                    if abs(pos_g1[j] - i) <= max(1, near_window):
                        found_near = True
                        break
                if found_near:
                    proximity_bonus = self.bonus_proximity

        base = (self.weight_vector * v) + (self.weight_fts * fts_signal)
        total = base + phrase_bonus + proximity_bonus + (self.weight_term_coverage * coverage)
        total = max(0.0, min(1.0, total))

        return ScoreBreakdown(
            vector_similarity=v,
            fts_signal=fts_signal,
            phrase_bonus=phrase_bonus,
            proximity_bonus=proximity_bonus,
            term_coverage=coverage,
            total=total,
        )


def serialize_breakdown(b: ScoreBreakdown) -> Dict[str, float]:
    return {
        "vector_similarity": round(b.vector_similarity, 4),
        "fts_signal": round(b.fts_signal, 4),
        "phrase_bonus": round(b.phrase_bonus, 4),
        "proximity_bonus": round(b.proximity_bonus, 4),
        "term_coverage": round(b.term_coverage, 4),
        "total": round(b.total, 4),
    }


__all__ = ["HybridScorer", "ScoreBreakdown", "serialize_breakdown"]


def _simple_tokenize(text: str) -> List[str]:
    import re
    return re.findall(r"[\w\u0600-\u06FF]+", text)
