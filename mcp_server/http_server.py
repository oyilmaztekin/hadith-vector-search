"""Flask HTTP server exposing MCP-style endpoints per collection.

Endpoints (per collection):
- GET  /health
- GET  /api/<collection>/status/vector
- GET  /api/<collection>/status/fts
- POST /api/<collection>/search/hybrid   { query, n_results, mode, weights... }

Run:
  python3 -m mcp_server.http_server --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse
from typing import Any, Dict

try:
    from flask import Flask, jsonify, request
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Flask is required: pip install Flask") from exc

from .tools import vector_index_status, fts_status, hybrid_search


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health() -> Any:  # pragma: no cover - trivial
        return jsonify({"ok": True})

    @app.get("/api/<collection>/status/vector")
    def api_vector_status(collection: str) -> Any:
        status = vector_index_status(collection=collection)
        return jsonify(status)

    @app.get("/api/<collection>/status/fts")
    def api_fts_status(collection: str) -> Any:
        status = fts_status(collection=collection)
        return jsonify(status)

    @app.post("/api/<collection>/search/hybrid")
    def api_hybrid_search(collection: str) -> Any:
        payload: Dict[str, Any] = request.get_json(silent=True) or {}
        query = payload.get("query")
        if not query:
            return jsonify({"error": "Missing 'query'"}), 400

        n_results = int(payload.get("n_results", 10))
        mode = payload.get("mode")
        # Optional weight overrides
        weight_vector = payload.get("weight_vector")
        weight_fts = payload.get("weight_fts")
        weight_term_coverage = payload.get("weight_term_coverage")
        bonus_phrase = payload.get("bonus_phrase")

        result = hybrid_search(
            query,
            n_results=n_results,
            mode=mode,
            collection=collection,
            weight_vector=weight_vector,
            weight_fts=weight_fts,
            weight_term_coverage=weight_term_coverage,
            bonus_phrase=bonus_phrase,
        )
        return jsonify(result)

    return app


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - dev runner
    parser = argparse.ArgumentParser(description="MCP HTTP server (Flask)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    context = ('cert/cert.pem', 'cert/key.pem')  # (cert, key)
    app = create_app()
    app.run(host=args.host, port=args.port, ssl_context=context)


if __name__ == "__main__":  # pragma: no cover
    main()
