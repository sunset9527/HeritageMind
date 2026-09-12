"""AI search keeps local evidence available when optional tools are unavailable."""

import asyncio


def test_ai_search_aggregates_local_evidence_and_reports_optional_tool_status():
    from src.services.ai_search import AiSearchService
    from src.services.mcp_tools import McpToolResult

    async def unavailable(_: str):
        return McpToolResult(status="not_configured", message="Web search is not configured")

    service = AiSearchService(
        retrieve=lambda query: [{"title": "Local craft", "content": "Local evidence", "source": "knowledge_base"}],
        graph=lambda query: {"nodes": [{"name": "Test Craft"}], "edges": []},
        media=lambda query: [{"title": "Test image", "url": "/media/1"}],
        optional_tools={"web": unavailable},
    )

    result = asyncio.run(service.search("test craft"))

    assert result["citations"] == [{"title": "Local craft", "source": "knowledge_base"}]
    assert result["graph"]["nodes"][0]["name"] == "Test Craft"
    assert result["media"][0]["title"] == "Test image"
    assert result["sources"]["web"]["status"] == "not_configured"
    assert result["answer_status"] == "evidence_only"
