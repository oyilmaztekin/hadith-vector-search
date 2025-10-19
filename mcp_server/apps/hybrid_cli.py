"""Interactive CLI to test hybrid_search with tunable weights."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional

from ..tools import hybrid_search


def run_once(query: str, n_results: int, args: argparse.Namespace) -> int:
    t0 = time.perf_counter()
    res = hybrid_search(
        query,
        n_results=n_results,
        mode=args.mode,
        weight_vector=args.weight_vector,
        weight_fts=args.weight_fts,
        weight_term_coverage=args.weight_term_coverage,
        bonus_phrase=args.bonus_phrase,
    )
    dt = (time.perf_counter() - t0) * 1000

    if args.json:
        print(json.dumps({"time_ms": round(dt, 2), **res}, ensure_ascii=False, indent=2))
        return 0

    print(f"intent={res['intent']} mode={res.get('mode')} time_ms={dt:.1f} candidates={res['total_candidates']}")
    w = res.get("weights", {})
    print(
        "weights -> vector={wv:.2f} fts={wf:.2f} term_cov={wt:.2f} phrase+={bp:.2f} prox+={bpr:.2f}".format(
            wv=w.get("weight_vector", 0.0),
            wf=w.get("weight_fts", 0.0),
            wt=w.get("weight_term_coverage", 0.0),
            bp=w.get("bonus_phrase", 0.0),
            bpr=w.get("bonus_proximity", 0.0),
        )
    )
    for i, h in enumerate(res.get("hits", []), 1):
        print(
            f" {i}. {h['doc_id']} score={h['score']:.3f} narrator={h.get('narrator')}\n"
            f"     breakdown={json.dumps(h['breakdown'])}\n"
            f"     snippet={(h.get('snippet') or '')[:200]!r}"
        )
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hybrid search CLI tester")
    parser.add_argument("query", nargs="?", help="Query string. If omitted, enters REPL mode")
    parser.add_argument("-k", "--n-results", type=int, default=5, help="Number of results to show")
    parser.add_argument("--mode", choices=["balanced", "term-priority"], help="Preset mode for weights")
    parser.add_argument("--weight-vector", type=float, help="Weight for vector similarity (overrides mode)")
    parser.add_argument("--weight-fts", type=float, help="Weight for FTS signal (overrides mode)")
    parser.add_argument("--weight-term-coverage", type=float, help="Weight for term coverage (overrides mode)")
    parser.add_argument("--bonus-phrase", type=float, help="Bonus for phrase match (overrides mode)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args(argv)

    if args.query:
        return run_once(args.query, args.n_results, args)

    # REPL mode
    print("Hybrid Search REPL. Type 'exit' to quit.")
    while True:
        try:
            q = input("query> ").strip()
        except EOFError:
            print()
            break
        if not q or q.lower() in {"exit", "quit", "q"}:
            break
        try:
            run_once(q, args.n_results, args)
        except Exception as exc:
            print(f"Error: {exc}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
