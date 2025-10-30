"""FastMCP HTTP server exposing Quran tafsir tools."""

from __future__ import annotations

import argparse
from typing import Sequence

from .server import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_STREAM_PATH, create_server


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI flags for the HTTP transport runner."""

    parser = argparse.ArgumentParser(
        description="Run the Quran tafsir MCP server over Streamable HTTP.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help=f"Bind host (default: {DEFAULT_HOST}, or QURAN_MCP_HOST env).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"Bind port (default: {DEFAULT_PORT}, or QURAN_MCP_PORT env).",
    )
    parser.add_argument(
        "--path",
        dest="stream_path",
        default=None,
        help=(
            f"HTTP path for MCP endpoint (default: {DEFAULT_STREAM_PATH}, "
            "or QURAN_MCP_PATH env)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for running the HTTP transport server."""

    args = parse_args(argv)
    server = create_server(
        host=args.host,
        port=args.port,
        stream_path=args.stream_path,
    )
    try:
        server.run(transport="streamable-http")
    except KeyboardInterrupt:  # pragma: no cover - manual shutdown
        pass


if __name__ == "__main__":
    main()
