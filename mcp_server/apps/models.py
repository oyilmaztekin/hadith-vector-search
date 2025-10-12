"""Pydantic models for hadith ingestion and normalization."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .normalization import extract_narrator_name


class TextSegment(BaseModel):
    language: str = Field(..., description="Language code, e.g., 'en' or 'ar'")
    content: str = Field(..., description="Text content")


class Reference(BaseModel):
    label: str
    value: str


class HadithDocument(BaseModel):
    collection_slug: str
    collection_name: str
    book_id: str
    book_title_en: str
    book_title_ar: str
    chapter_id: str
    chapter_number_en: Optional[str] = None
    chapter_number_ar: Optional[str] = None
    chapter_title_en: Optional[str] = None
    chapter_title_ar: Optional[str] = None
    hadith_id_site: str
    hadith_num_global: Optional[str] = None
    hadith_num_in_book: Optional[str] = None
    texts: List[TextSegment]
    narrator: Optional[str] = None
    grading: List[str] = Field(default_factory=list)
    references: List[Reference] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    footnotes: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    scraped_at: Optional[datetime] = None
    checksum: Optional[str] = None

    canonical_narrator: Optional[str] = Field(
        default=None,
        description="Normalized narrator name without honorifics or verbs.",
    )

    model_config = {
        "extra": "ignore",
    }

    @field_validator("texts")
    @classmethod
    def validate_bilingual_text(cls, value: List[TextSegment]) -> List[TextSegment]:
        languages = {segment.language for segment in value}
        if languages != {"en", "ar"}:
            raise ValueError(f"Expected English and Arabic texts, found {languages}")
        return value

    @model_validator(mode="after")
    def set_canonical_narrator(self) -> "HadithDocument":
        self.canonical_narrator = extract_narrator_name(self.narrator)
        return self


class BookStats(BaseModel):
    book_id: str
    total_hadith: int
    unique_narrators: int
    checksum_examples: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class IngestionResult(BaseModel):
    book_id: str
    ingested_count: int
    skipped_count: int
    stats: BookStats
    duration_seconds: float


__all__ = [
    "TextSegment",
    "Reference",
    "HadithDocument",
    "BookStats",
    "IngestionResult",
]
