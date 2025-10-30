"""MCP stdio server exposing Quran tafsir lookup and search tools."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Sequence

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "The 'mcp' package is required. Install with: pip install mcp"
    ) from exc

try:  # pragma: no cover - work across SDK variants
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
        ServerResult,
        TextContent,
        Tool,
    )
except Exception:  # pragma: no cover
    CallToolRequest = None  # type: ignore[assignment]
    CallToolResult = None  # type: ignore[assignment]
    ListToolsRequest = None  # type: ignore[assignment]
    ListToolsResult = None  # type: ignore[assignment]
    ServerResult = None  # type: ignore[assignment]
    TextContent = None  # type: ignore[assignment]
    Tool = None  # type: ignore[assignment]

from .search import QuranSearchIndex

server = Server("quran-tafsir-mcp")
_index = QuranSearchIndex()


_TOOL_DEFINITIONS: Sequence[Dict[str, Any]] = (
    {
        "name": "search_tafsir",
        "description": "Full-text search over the Ibn Kathir (Abridged) tafsir",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                "mode": {
                    "type": "string",
                    "enum": ["hybrid", "semantic", "vector", "fts"],
                    "default": "hybrid",
                },
                "weight_vector": {"type": "number"},
                "weight_fts": {"type": "number"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_verse",
        "description": "Fetch tafsir entry by verse",
        "inputSchema": {
            "type": "object",
            "properties": {
                "surah": {"type": "integer", "minimum": 1, "maximum": 114},
                "ayah": {"type": "integer", "minimum": 1},
                "verse_key": {"type": "string"},
            },
        },
    },
    {
        "name": "index_status",
        "description": "Return index statistics",
        "inputSchema": {"type": "object"},
    },
)


def _tool_models() -> Optional[Sequence[Any]]:
    if Tool is None:
        return None
    return tuple(Tool(**definition) for definition in _TOOL_DEFINITIONS)


def _structured_result(
    data: Any | None = None,
    *,
    is_error: bool = False,
    text: Optional[str] = None,
) -> Any:
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


def _format_entry(entry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return entry or {}


def _verse_lookup(args: Dict[str, Any]) -> Dict[str, Any]:
    verse_key = args.get("verse_key")
    entry = None
    if verse_key:
        entry_obj = _index.get(str(verse_key))
        if entry_obj:
            entry = {
                "verse_key": entry_obj.verse_key,
                "surah": entry_obj.surah,
                "ayah": entry_obj.ayah,
                "resource": entry_obj.resource_name,
                "text_html": entry_obj.text_html,
                "text_plain": entry_obj.text_plain,
            }
    else:
        surah = args.get("surah")
        ayah = args.get("ayah")
        if surah is not None and ayah is not None:
            entry_obj = _index.get_by_surah(int(surah), int(ayah))
            if entry_obj:
                entry = {
                    "verse_key": entry_obj.verse_key,
                    "surah": entry_obj.surah,
                    "ayah": entry_obj.ayah,
                    "resource": entry_obj.resource_name,
                    "text_html": entry_obj.text_html,
                    "text_plain": entry_obj.text_plain,
                }
    if entry is None:
        return {
            "error": "Verse not found",
            "input": {
                "verse_key": verse_key,
                "surah": args.get("surah"),
                "ayah": args.get("ayah"),
            },
        }
    return entry


async def call_tool(name: str, args: Dict[str, Any]) -> Any:
    if name == "search_tafsir":
        result = _index.search(
            args.get("query", ""),
            limit=int(args.get("limit", 5)),
            mode=args.get("mode", "hybrid"),
            weight_vector=args.get("weight_vector"),
            weight_fts=args.get("weight_fts"),
        )
        return _structured_result(result)
    if name == "get_verse":
        result = _verse_lookup(args)
        if "error" in result:
            return _structured_result(result, is_error=True)
        return _structured_result(result)
    if name == "index_status":
        result = _index.status()
        return _structured_result(result)
    return _structured_result({"error": f"Unknown tool: {name}"}, is_error=True)


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
    if hasattr(server, "request_handlers") and isinstance(server.request_handlers, dict):
        if ListToolsRequest is not None and CallToolRequest is not None:
            server.request_handlers[ListToolsRequest] = handle_list_tools_handler  # type: ignore[index]
            server.request_handlers[CallToolRequest] = handle_call_tool_handler  # type: ignore[index]
        else:
            server.request_handlers["tools/list"] = handle_list_tools_handler
            server.request_handlers["tools/call"] = handle_call_tool_handler
        return
    setter = getattr(server, "set_request_handler", None)
    if callable(setter):
        setter("tools/list", handle_list_tools_handler)
        setter("tools/call", handle_call_tool_handler)
        return


async def main() -> None:  # pragma: no cover
    _register_handlers()
    async with stdio_server() as (r, w):
        try:
            await server.run(r, w)
        except TypeError:
            await server.run(r, w, {})


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
