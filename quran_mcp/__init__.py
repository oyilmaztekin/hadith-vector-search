"""Model Context Protocol server utilities for the Quran tafsir dataset."""

from .loader import QuranCorpus, TafsirEntry
from .search import QuranSearchIndex

__all__ = ["QuranCorpus", "TafsirEntry", "QuranSearchIndex"]
