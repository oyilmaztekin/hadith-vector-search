# Quran Tafsir MCP Server

This module exposes the Ibn Kathir (Abridged) tafsir dataset via the Model Context Protocol (MCP). It provides tools for verse lookup and hybrid (BM25 + semantic embedding) search so MCP-compatible clients (e.g., ChatGPT MCP beta, Claude MCP) can reference tafsir passages during a conversation.

## Available Tools

- `search_tafsir` – Hybrid search over the tafsir corpus using SQLite FTS5 and sentence-transformer embeddings (modes: `hybrid`, `semantic`, `fts`).
  - Optional knobs: `mode`, `weight_vector`, `weight_fts`, `dedupe` (filters duplicate passages that span multiple ayat).
- `get_verse` – Fetch a tafsir record by `verse_key` or (`surah`, `ayah`). Returns both raw HTML and plain-text versions.
- `index_status` – Diagnostic information about the in-memory index.

## Streamable HTTP Transport

Start the HTTP server using the FastMCP Streamable HTTP transport (defaults to `http://127.0.0.1:8000/mcp`):

```bash
python3 -m quran_mcp.mcp_http --host 127.0.0.1 --port 8000 --path /mcp
```

You can also control the bind address via `QURAN_MCP_HOST`, `QURAN_MCP_PORT`, and `QURAN_MCP_PATH`. The legacy stdio runner (`python3 -m quran_mcp.mcp_stdio`) remains available for clients that do not yet support HTTP transport.

## Running with the Python MCP SDK

1. Install the MCP Python SDK (if you have not already):
   ```bash
   pip install "git+https://github.com/modelcontextprotocol/python-sdk.git#egg=mcp"
   ```
2. Install fastMCP runtime:
   ```bash
   pip install fastmcp
   ```
3. Launch the HTTP server in a separate terminal:
   ```bash
   python3 -m quran_mcp.mcp_http --host 127.0.0.1 --port 8000 --path /mcp
   ```
4. Point your MCP client (or the MCP Inspector) at `http://127.0.0.1:8000/mcp`.

## ChatGPT MCP Integration (STDIO fallback)

ChatGPT MCP currently expects stdio transport. Configure it with:

- **Command**: `python3`
- **Arguments**: `-m`, `quran_mcp.mcp_stdio` (stdio fallback)
- **Working directory**: repository root (so `data/quran/` is reachable)

## Claude Desktop Integration (STDIO fallback)

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

## Local Smoke Test

```bash
python - <<'PY'
from quran_mcp.search import QuranSearchIndex

index = QuranSearchIndex()
print('Index status:', index.status())
print('Hybrid sample:', index.search('divine mercy', limit=3))
print('Semantic only:', index.search('compassion for believers', limit=3, mode='semantic'))
PY
```

The first semantic query will download the embedding model; keep the machine online or pre-populate your Hugging Face cache.

## ChatGPT MCP Integration (STDIO fallback)

1. Ensure the MCP SDK is installed (`pip install "git+https://github.com/modelcontextprotocol/python-sdk.git#egg=mcp"`).
2. ChatGPT MCP currently expects stdio transport. Add a connection with:
   - Command: `python3`
   - Arguments: `-m`, `quran_mcp.mcp_stdio`
   - Working directory: repository root
3. Invoke tools from the chat, e.g.:

   ```json
   {
     "tool": "search_tafsir",
     "arguments": {"query": "compassion for believers", "mode": "hybrid", "limit": 3}
   }
   ```

## Claude Desktop Integration (STDIO fallback)

Add a server entry to `clio.json`:

```json
{
  "servers": [
    {
      "id": "quran-tafsir",
      "command": "python3",
      "args": ["-m", "quran_mcp.mcp_stdio"],
      "workingDirectory": "/absolute/path/to/repo",
      "env": {
        "QURAN_MCP_DATA_DIR": "/absolute/path/to/repo/data/quran"
      }
    }
  ]
}
```

Restart Claude Desktop, enable the tool, and issue MCP calls such as `search_tafsir` with `mode` set to `hybrid`, `semantic`, or `fts`.
