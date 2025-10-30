from __future__ import annotations

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mcp_server import mcp_stdio


def _run_async(coro):
    return asyncio.run(coro)


class MCPStdioTests(unittest.TestCase):
    def test_list_tools_contains_expected_names(self) -> None:
        tools = mcp_stdio.list_tools()["tools"]
        names = {tool["name"] for tool in tools}
        self.assertTrue({"hybrid_search", "fts_status", "vector_index_status", "fts_match"} <= names)

    def test_handle_list_tools_handler_returns_server_result(self) -> None:
        res = _run_async(mcp_stdio.handle_list_tools_handler())
        if mcp_stdio.ServerResult is not None and mcp_stdio.ListToolsResult is not None:
            self.assertIsInstance(res, mcp_stdio.ServerResult)
            tools = res.root.tools  # type: ignore[attr-defined]
            names = {tool.name for tool in tools}
            self.assertIn("hybrid_search", names)
        else:
            self.assertIsInstance(res, dict)
            self.assertIn("tools", res)

    def test_call_tool_returns_structured_result(self) -> None:
        with patch("mcp_server.mcp_stdio.do_hybrid_search", return_value={"query": "mercy", "hits": [{"doc_id": "1"}]}):
            result = _run_async(mcp_stdio.call_tool("hybrid_search", {"query": "mercy"}))

        if mcp_stdio.CallToolResult is not None:
            self.assertIsInstance(result, mcp_stdio.CallToolResult)
            self.assertFalse(result.isError)
            self.assertEqual(result.structuredContent, {"query": "mercy", "hits": [{"doc_id": "1"}]})
        else:
            self.assertEqual(result["content"][0]["type"], "json")

    def test_handle_call_tool_handler_unknown_tool(self) -> None:
        res = _run_async(mcp_stdio.handle_call_tool_handler(name="nonexistent"))

        if mcp_stdio.ServerResult is not None:
            self.assertIsInstance(res, mcp_stdio.ServerResult)
            payload = res.root  # type: ignore[attr-defined]
            self.assertTrue(payload.isError)
        else:
            self.assertTrue(res.get("isError"))

    def test_handle_call_tool_handler_reads_request_object(self) -> None:
        with patch("mcp_server.mcp_stdio.do_fts_status", return_value={"ok": True, "collection": "riyad"}):
            params = SimpleNamespace(name="fts_status", arguments={"collection": "riyad"})
            request = SimpleNamespace(params=params)
            res = _run_async(mcp_stdio.handle_call_tool_handler(request))

        if mcp_stdio.ServerResult is not None:
            self.assertIsInstance(res, mcp_stdio.ServerResult)
            payload = res.root  # type: ignore[attr-defined]
            self.assertEqual(payload.structuredContent, {"ok": True, "collection": "riyad"})
        else:
            json_content = res["content"][0]
            self.assertEqual(json_content["data"]["collection"], "riyad")

    def test_register_handlers_prefers_type_keys(self) -> None:
        class DummyServer:
            def __init__(self) -> None:
                self.request_handlers: dict = {}

        dummy = DummyServer()
        dummy_list = type("DummyList", (), {})
        dummy_call = type("DummyCall", (), {})

        with patch("mcp_server.mcp_stdio.server", dummy, create=True), patch(
            "mcp_server.mcp_stdio.ListToolsRequest", dummy_list, create=True
        ), patch("mcp_server.mcp_stdio.CallToolRequest", dummy_call, create=True):
            mcp_stdio._register_handlers()

        self.assertIs(dummy.request_handlers[dummy_list], mcp_stdio.handle_list_tools_handler)
        self.assertIs(dummy.request_handlers[dummy_call], mcp_stdio.handle_call_tool_handler)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
