"""Data models for Sunnah.com scraping pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, computed_field, model_validator


class HadithText(BaseModel):
    """Container for a hadith text in a specific language."""

    language: Literal["ar", "en"]
    content: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def strip_whitespace(self) -> "HadithText":
        self.content = self.content.strip()
        return self


class GradingEntry(BaseModel):
    """Represents a grading given by a scholar."""

    scholar: str
    grade: Optional[str] = None
    note: Optional[str] = None


class ReferenceEntry(BaseModel):
    """Represents a reference mapping for a hadith."""

    label: str
    value: str


class HadithRecord(BaseModel):
    """Normalized hadith payload for downstream processing."""

    collection_slug: str = Field(default="riyadussalihin")
    collection_name: str = Field(default="Riyad as-Salihin")
    book_id: str
    book_title_en: str
    book_title_ar: Optional[str] = None
    chapter_id: Optional[str] = None
    chapter_number_en: Optional[str] = None
    chapter_number_ar: Optional[str] = None
    chapter_title_en: Optional[str] = None
    chapter_title_ar: Optional[str] = None
    hadith_id_site: str
    hadith_num_global: Optional[str] = None
    hadith_num_in_book: Optional[str] = None
    texts: list[HadithText]
    narrator: Optional[str] = None
    grading: list[GradingEntry] = Field(default_factory=list)
    references: list[ReferenceEntry] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    footnotes: list[str] = Field(default_factory=list)
    source_url: HttpUrl
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def ensure_text_languages(self) -> "HadithRecord":
        languages = {text.language for text in self.texts}
        missing = {"ar", "en"} - languages
        if missing:
            raise ValueError(f"HadithRecord texts missing required languages: {missing}")
        return self

    @computed_field
    @property
    def checksum(self) -> str:
        payload = "\u241f".join([
            self.collection_slug,
            self.book_id,
            self.hadith_id_site,
            "\u241f".join(text.content for text in self.texts),
        ])
        return sha256(payload.encode("utf-8")).hexdigest()


class BookIndexEntry(BaseModel):
    """Minimal metadata about a book within a collection."""

    book_id: str
    source_url: HttpUrl
    book_number: Optional[str] = None
    book_title_en: str
    book_title_ar: Optional[str] = None
    hadith_count: int
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
