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
from typing import Any, Dict, Optional, Sequence

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "The 'mcp' package is required. Install with: pip install mcp"
    ) from exc

try:  # pragma: no cover - support multiple SDK versions gracefully
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
        ServerResult,
        TextContent,
        Tool,
    )
except Exception:  # Older SDKs expose plain dict interfaces
    CallToolRequest = None  # type: ignore[assignment]
    CallToolResult = None  # type: ignore[assignment]
    ListToolsRequest = None  # type: ignore[assignment]
    ListToolsResult = None  # type: ignore[assignment]
    ServerResult = None  # type: ignore[assignment]
    TextContent = None  # type: ignore[assignment]
    Tool = None  # type: ignore[assignment]

from .tools import hybrid_search as do_hybrid_search
from .tools import fts_status as do_fts_status
from .tools import vector_index_status as do_vector_status
from .apps.fts import FTSIndex


server = Server("hadith-mcp")


_TOOL_DEFINITIONS: Sequence[Dict[str, Any]] = (
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
)


def _tool_models() -> Optional[Sequence[Any]]:
    if Tool is None:
        return None
    return tuple(Tool(**definition) for definition in _TOOL_DEFINITIONS)


def _structured_result(data: Any | None = None, *, is_error: bool = False, text: Optional[str] = None) -> Any:
    if CallToolResult is not None:
        content = [TextContent(type="text", text=text)] if text and TextContent is not None else []
        kwargs: Dict[str, Any] = {"content": content, "isError": is_error}
        if data is not None:
            kwargs["structuredContent"] = data
        return CallToolResult(**kwargs)

    payload: Dict[str, Any] = {"content": []}
    if data is not None:
        payload["content"].append({"type": "json", "data": data})
    if text:
        payload["content"].append({"type": "text", "text": text})
    if not payload["content"]:
        payload["content"].append({"type": "text", "text": ""})
    if is_error:
        payload["isError"] = True
    return payload


def list_tools() -> Dict[str, Any]:
    return {"tools": [dict(tool) for tool in _TOOL_DEFINITIONS]}


async def call_tool(name: str, args: Dict[str, Any]) -> Any:
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
        return _structured_result(data)

    if name == "fts_status":
        data = do_fts_status(collection=args.get("collection"))
        return _structured_result(data)

    if name == "vector_index_status":
        data = do_vector_status(collection=args.get("collection"))
        return _structured_result(data)

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
            return _structured_result({"error": "Provide match or en/ar/narrator"}, is_error=True)
        try:
            rows = idx.search_match(expr, limit=int(args.get("limit", 10)))
        except Exception as exc:
            return _structured_result({"error": str(exc), "match": expr}, is_error=True)
        return _structured_result({"match": expr, "hits": rows})

    return _structured_result(is_error=True, text=f"Unknown tool: {name}")


def _refresh_tool_cache(models: Sequence[Any]) -> None:
    cache = getattr(server, "_tool_cache", None)
    if isinstance(cache, dict):
        cache.clear()
        for model in models:
            name = getattr(model, "name", None)
            if name is not None:
                cache[name] = model


async def handle_list_tools_handler(request: Any | None = None, **_: Any) -> Any:
    raw = list_tools()
    if ListToolsResult is not None and ServerResult is not None and Tool is not None:
        models = _tool_models() or ()
        _refresh_tool_cache(models)
        return ServerResult(ListToolsResult(tools=list(models)))
    return raw


async def handle_call_tool_handler(
    request: Any | None = None,
    *,
    name: Optional[str] = None,
    arguments: Optional[Dict[str, Any]] = None,
    **_: Any,
) -> Any:
    if request is not None and hasattr(request, "params"):
        params = getattr(request, "params")
        name = getattr(params, "name", name)
        arguments = getattr(params, "arguments", arguments)

    if not name:
        result = _structured_result(is_error=True, text="Missing tool name")
    else:
        result = await call_tool(name, arguments or {})

    if CallToolResult is not None and ServerResult is not None and isinstance(result, CallToolResult):
        return ServerResult(result)
    return result


def _register_handlers() -> None:
    # Register handlers in a way that works across SDK variants
    if hasattr(server, "request_handlers") and isinstance(server.request_handlers, dict):
        # Modern SDKs key request handlers by request type, older ones by method string
        if ListToolsRequest is not None and CallToolRequest is not None:
            server.request_handlers[ListToolsRequest] = handle_list_tools_handler  # type: ignore[index]
            server.request_handlers[CallToolRequest] = handle_call_tool_handler  # type: ignore[index]
        else:
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
