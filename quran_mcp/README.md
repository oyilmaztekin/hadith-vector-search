# Quran Tafsir MCP Server

This module exposes the Ibn Kathir (Abridged) tafsir dataset via the Model Context Protocol (MCP). It provides tools for verse lookup and hybrid (BM25 + semantic embedding) search so MCP-compatible clients (e.g., ChatGPT MCP beta, Claude MCP) can reference tafsir passages during a conversation.

## Available Tools

- `search_tafsir` – Hybrid search over the tafsir corpus using SQLite FTS5 and sentence-transformer embeddings (modes: `hybrid`, `semantic`, `fts`).
- `get_verse` – Fetch a tafsir record by `verse_key` or (`surah`, `ayah`). Returns both raw HTML and plain-text versions.
- `index_status` – Diagnostic information about the in-memory index.

## Running with the Python MCP SDK

1. Install the MCP Python SDK (if you have not already):
   ```bash
   pip install "git+https://github.com/modelcontextprotocol/python-sdk.git#egg=mcp"
   ```
2. Launch the server with the MCP Inspector:
   ```bash
   npx -y @modelcontextprotocol/inspector --command "python3 -m quran_mcp.mcp_stdio"
   ```

## ChatGPT MCP Integration

In the ChatGPT MCP settings add a new connection with:

- **Command**: `python3`
- **Arguments**: `-m`, `quran_mcp.mcp_stdio`
- **Working directory**: repository root (so `data/quran/` is reachable)

## Claude Desktop Integration

Create or update your `clio.json` (Claude tool configuration) with:

```json
{
  "servers": [
    {
      "id": "quran-tafsir",
      "command": "python3",
      "args": ["-m", "quran_mcp.mcp_stdio"],
      "workingDirectory": "/path/to/your/repo"
    }
  ]
}
```

Restart Claude Desktop and enable the `quran-tafsir` tool from the Tools panel.

## Notes

- The server builds an in-memory FTS5 index on first use; expect a short initial load while the JSONL corpus is parsed.
- Semantic search uses `sentence-transformers/all-MiniLM-L6-v2`; the first query will also build/cache embeddings under `data/indexes/quran/` (subsequent runs reuse them).
- All responses include the `verse_key` so you can cross-reference the tafsir with your own Quran text source.
- To point at a different dataset location set `QURAN_MCP_DATA_DIR=/path/to/quran/jsonl` before launching. To use a different embedding model set `QURAN_MCP_MODEL=<sentence-transformers model>`.
