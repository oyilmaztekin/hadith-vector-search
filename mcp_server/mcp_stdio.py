"""Python MCP stdio server exposing hadith search tools (SDK-agnostic style).

If your installed `mcp` Python SDK lacks the `@server.tool` decorator, this
server uses request handlers for `tools/list` and `tools/call`, which are
available across SDK versions.

Run locally (Inspector):
  npx -y @modelcontextprotocol/inspector --command "python3 -m mcp_server.mcp_stdio"

Add to ChatGPT MCP connections:
  Command: python3
  Args: -m, mcp_server.mcp_stdio
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "The 'mcp' package is required. Install with: pip install mcp"
    ) from exc

from .tools import hybrid_search as do_hybrid_search
from .tools import fts_status as do_fts_status
from .tools import vector_index_status as do_vector_status
from .apps.fts import FTSIndex


server = Server("hadith-mcp")


def list_tools() -> Dict[str, Any]:
    return {
        "tools": [
            {
                "name": "hybrid_search",
                "description": "Hybrid search over hadith corpus",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "n_results": {"type": "integer", "default": 10, "minimum": 1},
                        "mode": {"type": "string", "enum": ["balanced", "term-priority"]},
                        "collection": {"type": "string", "default": "riyadussalihin"},
                        "weight_vector": {"type": "number"},
                        "weight_fts": {"type": "number"},
                        "weight_term_coverage": {"type": "number"},
                        "bonus_phrase": {"type": "number"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "fts_status",
                "description": "FTS index status",
                "inputSchema": {"type": "object", "properties": {"collection": {"type": "string"}}},
            },
            {
                "name": "vector_index_status",
                "description": "Vector index status",
                "inputSchema": {"type": "object", "properties": {"collection": {"type": "string"}}},
            },
            {
                "name": "fts_match",
                "description": "Run raw FTS MATCH query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "match": {"type": "string"},
                        "en": {"type": "string"},
                        "ar": {"type": "string"},
                        "narrator": {"type": "string"},
                        "limit": {"type": "integer", "default": 10, "minimum": 1},
                        "collection": {"type": "string", "default": "riyadussalihin"},
                    },
                },
            },
        ]
    }


async def call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "hybrid_search":
        data = do_hybrid_search(
            args.get("query"),
            n_results=int(args.get("n_results", 10)),
            mode=args.get("mode"),
            collection=args.get("collection"),
            weight_vector=args.get("weight_vector"),
            weight_fts=args.get("weight_fts"),
            weight_term_coverage=args.get("weight_term_coverage"),
            bonus_phrase=args.get("bonus_phrase"),
        )
        return {"content": [{"type": "json", "data": data}]}

    if name == "fts_status":
        data = do_fts_status(collection=args.get("collection"))
        return {"content": [{"type": "json", "data": data}]}

    if name == "vector_index_status":
        data = do_vector_status(collection=args.get("collection"))
        return {"content": [{"type": "json", "data": data}]}

    if name == "fts_match":
        def _quote_if_needed(text: str) -> str:
            t = text.strip()
            if not t:
                return t
            if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
                return t
            if any(c.isspace() for c in t):
                return f'"{t}"'
            return t

        def _build_match(en: Optional[str], ar: Optional[str], narrator: Optional[str]) -> Optional[str]:
            parts = []
            if en:
                parts.append(f"english_text:{_quote_if_needed(en)}")
            if ar:
                parts.append(f"arabic_text:{_quote_if_needed(ar)}")
            if narrator:
                parts.append(f"narrator:{_quote_if_needed(narrator)}")
            return " AND ".join(parts) if parts else None

        col = (args.get("collection") or "riyadussalihin").lower()
        db = (
            "data/indexes/fts/hadith.db"
            if col == "riyadussalihin"
            else f"data/indexes/{col}/fts.db"
        )
        idx = FTSIndex(db_path=Path(db))
        expr = args.get("match") or _build_match(args.get("en"), args.get("ar"), args.get("narrator"))
        if not expr:
            return {"content": [{"type": "json", "data": {"error": "Provide match or en/ar/narrator"}}]}
        try:
            rows = idx.search_match(expr, limit=int(args.get("limit", 10)))
        except Exception as exc:
            return {"content": [{"type": "json", "data": {"error": str(exc), "match": expr}}]}
        return {"content": [{"type": "json", "data": {"match": expr, "hits": rows}}]}

    return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]} 


async def handle_list_tools_handler(**_: Any) -> Any:
    return list_tools()


async def handle_call_tool_handler(name: Optional[str] = None, arguments: Optional[Dict[str, Any]] = None, **_: Any) -> Any:
    if not name:
        return {"content": [{"type": "text", "text": "Missing tool name"}]}
    return await call_tool(name, arguments or {})


def _register_handlers() -> None:
    # Register handlers in a way that works across SDK variants
    if hasattr(server, "request_handlers") and isinstance(server.request_handlers, dict):
        server.request_handlers["tools/list"] = handle_list_tools_handler
        server.request_handlers["tools/call"] = handle_call_tool_handler
        return
    # Fallback: try attribute-based registration methods if present
    # Some SDKs might expose 'set_request_handler'
    seth = getattr(server, "set_request_handler", None)
    if callable(seth):
        seth("tools/list", handle_list_tools_handler)
        seth("tools/call", handle_call_tool_handler)
        return


async def main() -> None:  # pragma: no cover - entrypoint
    _register_handlers()
    async with stdio_server() as (r, w):
        try:
            # Newer SDKs may accept (r, w) only
            await server.run(r, w)
        except TypeError:
            # Some SDK versions require an initialization_options dict
            await server.run(r, w, {})


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
