"""Safe, reusable implementations behind the v2 MCP tools."""

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(frozen=True)
class McpToolResult:
    status: str
    items: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""


async def _get_json(url: str, *, params: dict[str, Any], client: Any | None = None) -> Any:
    if client is not None:
        response = await client.get(url, params=params)
        if response.status_code >= 400:
            raise RuntimeError(f"upstream returned {response.status_code}")
        return response.json()
    timeout = httpx.Timeout(5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as request_client:
        response = await request_client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def search_wikipedia(query: str, *, client: Any | None = None, limit: int = 5) -> McpToolResult:
    try:
        payload = await _get_json(
            "https://zh.wikipedia.org/w/rest.php/v1/search/page",
            params={"q": query.strip(), "limit": min(max(limit, 1), 10)},
            client=client,
        )
    except Exception:
        return McpToolResult(status="unavailable", message="Wikipedia temporarily unavailable")
    items = []
    for page in payload.get("pages", [])[:limit]:
        title = str(page.get("title", "")).strip()
        if title:
            items.append({
                "title": title,
                "summary": str(page.get("description", "")).strip(),
                "url": f"https://zh.wikipedia.org/wiki/{title.replace(' ', '_')}",
            })
    return McpToolResult(status="ok", items=items)


async def search_github(query: str, *, client: Any | None = None, limit: int = 5) -> McpToolResult:
    try:
        payload = await _get_json(
            "https://api.github.com/search/repositories",
            params={"q": query.strip(), "per_page": min(max(limit, 1), 10)}, client=client,
        )
    except Exception:
        return McpToolResult(status="unavailable", message="GitHub temporarily unavailable")
    return McpToolResult(status="ok", items=[{
        "title": item.get("full_name", ""), "summary": item.get("description") or "",
        "url": item.get("html_url", ""),
    } for item in payload.get("items", [])[:limit]])


async def search_web(query: str, *, endpoint: str, api_key: str, client: Any | None = None) -> McpToolResult:
    if not endpoint.strip() or not api_key.strip():
        return McpToolResult(status="not_configured", message="Web search is not configured")
    if not endpoint.startswith("https://"):
        return McpToolResult(status="invalid_configuration", message="Web search endpoint must use HTTPS")
    try:
        payload = await _get_json(endpoint, params={"q": query.strip()}, client=client)
    except Exception:
        return McpToolResult(status="unavailable", message="Web search temporarily unavailable")
    return McpToolResult(status="ok", items=list(payload.get("items", []))[:5])


async def search_baidu_baike(query: str, *, endpoint: str, api_key: str, client: Any | None = None) -> McpToolResult:
    return await search_web(query, endpoint=endpoint, api_key=api_key, client=client)


def search_local_knowledge(query: str, *, retriever: Any) -> McpToolResult:
    """Expose existing local retrieval without any network dependency."""
    items = []
    for item in retriever.retrieve(query)[:5]:
        items.append({"title": item.get("title") or item.get("craft_name", "本地知识"), "summary": item.get("content", "")[:500], "url": "local://knowledge"})
    return McpToolResult(status="ok", items=items)
