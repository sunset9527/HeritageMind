"""stdio entry point for the HeritageMind MCP tool surface.

Install the optional ``mcp`` dependency from requirements before running this module.
"""

import asyncio

from src.services.mcp_tools import search_github, search_wikipedia


def run() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:  # pragma: no cover - depends on optional runtime
        raise SystemExit("MCP runtime is not installed; run pip install -r requirements.txt") from error

    server = FastMCP("HeritageMind")

    @server.tool()
    async def search_wikipedia_tool(query: str) -> dict:
        """Search Wikipedia for publicly available cultural background."""
        result = await search_wikipedia(query)
        return {"status": result.status, "items": result.items, "message": result.message}

    @server.tool()
    async def search_github_tool(query: str) -> dict:
        """Search public GitHub repositories relevant to the query."""
        result = await search_github(query)
        return {"status": result.status, "items": result.items, "message": result.message}

    server.run()


if __name__ == "__main__":
    run()
