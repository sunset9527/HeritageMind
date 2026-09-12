"""Deterministic aggregation layer for the v2 AI-search response."""

import asyncio
from collections.abc import Callable
from typing import Any

from src.services.mcp_tools import McpToolResult


class AiSearchService:
    def __init__(
        self,
        *,
        retrieve: Callable[[str], list[dict[str, Any]]],
        graph: Callable[[str], dict[str, Any]],
        media: Callable[[str], list[dict[str, Any]]],
        optional_tools: dict[str, Callable[[str], Any]] | None = None,
    ):
        self.retrieve, self.graph, self.media = retrieve, graph, media
        self.optional_tools = optional_tools or {}

    async def search(self, query: str) -> dict[str, Any]:
        evidence = self.retrieve(query)
        citations = []
        seen = set()
        for item in evidence:
            citation = {"title": item.get("title", ""), "source": item.get("source", "knowledge_base")}
            key = (citation["title"], citation["source"])
            if citation["title"] and key not in seen:
                citations.append(citation)
                seen.add(key)
        statuses = {}
        for name, tool in self.optional_tools.items():
            value = tool(query)
            result: McpToolResult = await value if asyncio.iscoroutine(value) else value
            statuses[name] = {"status": result.status, "message": result.message}
        return {
            "answer": "", "answer_status": "evidence_only", "citations": citations,
            "graph": self.graph(query), "media": self.media(query), "sources": statuses,
        }
