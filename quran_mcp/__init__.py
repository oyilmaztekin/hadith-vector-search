"""Model Context Protocol server utilities for the Quran tafsir dataset."""

from .loader import QuranCorpus, TafsirEntry
from .search import QuranSearchIndex
from .server import create_server

__all__ = ["QuranCorpus", "TafsirEntry", "QuranSearchIndex", "create_server"]
