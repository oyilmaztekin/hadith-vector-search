"""FTS-only CLI to search the SQLite index with raw MATCH expressions.

Examples:
  python3 -m mcp_server.apps.fts_cli 'narrator:"Abu Hurairah" AND english_text:charity' -k 5
  python3 -m mcp_server.apps.fts_cli --en '"Iman has sixty odd"' -k 3
  python3 -m mcp_server.apps.fts_cli --en 'support* family' --narrator 'Abu Hurairah'

If no arguments are provided, enters a simple REPL that accepts raw MATCH input.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, List

from .fts import FTSIndex


def _quote_if_needed(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    # If already quoted, keep as-is
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        return t
    # Quote if contains whitespace or special chars
    if any(c.isspace() for c in t):
        return f'"{t}"'
    return t


def build_match(en: Optional[str], ar: Optional[str], narrator: Optional[str]) -> Optional[str]:
    parts: List[str] = []
    if en:
        parts.append(f"english_text:{_quote_if_needed(en)}")
    if ar:
        parts.append(f"arabic_text:{_quote_if_needed(ar)}")
    if narrator:
        parts.append(f"narrator:{_quote_if_needed(narrator)}")
    return " AND ".join(parts) if parts else None


def run_match(match: str, limit: int, as_json: bool) -> int:
    fts = FTSIndex()
    try:
        rows = fts.search_match(match, limit=limit)
    except Exception as exc:
        print(f"FTS error: {exc}")
        return 1

    if as_json:
        print(json.dumps({"match": match, "hits": rows}, ensure_ascii=False, indent=2))
        return 0

    print(f"MATCH: {match}")
    print(f"hits={len(rows)}")
    for i, r in enumerate(rows, 1):
        snippet = (r.get("english_text") or "").replace("\n", " ")[:240]
        print(
            f" {i}. {r.get('doc_id')} book={r.get('book_id')} chap={r.get('chapter_id')} narrator={r.get('narrator')} bm25={r.get('bm25')}\n"
            f"     {snippet!r}"
        )
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="FTS5 MATCH CLI over hadith index")
    parser.add_argument("match", nargs="?", help="Raw FTS MATCH expression")
    parser.add_argument("-k", "--limit", type=int, default=10, help="Max results to return")
    parser.add_argument("--en", help="English text tokens/phrase (builds english_text:...) ")
    parser.add_argument("--ar", help="Arabic text tokens/phrase (builds arabic_text:...) ")
    parser.add_argument("--narrator", help="Narrator exact/partial (builds narrator:...) ")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args(argv)

    match = args.match or build_match(args.en, args.ar, args.narrator)
    if match:
        return run_match(match, args.limit, args.json)

    # REPL mode
    print("FTS REPL. Enter raw MATCH strings (or 'exit'). Examples:")
    print("  english_text:fast* AND book_id:8")
    print("  narrator:\"Abu Hurairah\" AND english_text:charity")
    while True:
        try:
            line = input("fts> ").strip()
        except EOFError:
            print()
            break
        if not line or line.lower() in {"exit", "quit", "q"}:
            break
        run_match(line, args.limit, args.json)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

