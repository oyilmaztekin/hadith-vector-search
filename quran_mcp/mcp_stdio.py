"""FastMCP stdio runner exposing Quran tafsir tools."""

from __future__ import annotations

import asyncio

from .server import create_server


server = create_server()


if __name__ == "__main__":
    asyncio.run(server.run_stdio_async(show_banner=False))
