"""web_search — Tavily-backed general web search."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agentforge.core.tools.protocol import ToolResult
from agentforge.core.tools.validate import validate_input


class _Input(BaseModel):
    query: str = Field(min_length=1)
    max_results: int = Field(default=5, ge=1, le=10)


_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "maxResults": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
    },
    "required": ["query"],
    "additionalProperties": False,
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "results": {"type": "array"},
        "totalFound": {"type": "integer"},
    },
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _call(input_: dict[str, Any]) -> ToolResult:
    # Accept camelCase from the LLM; pydantic normalizes to snake_case.
    if "maxResults" in input_ and "max_results" not in input_:
        input_ = {**input_, "max_results": input_["maxResults"]}
    try:
        validated = validate_input(input_, _Input)
    except Exception as e:
        return ToolResult(data=None, error=str(e), retrievedAt=_now_iso())

    api_key = os.getenv("TAVILY_API_KEY")
    retrieved_at = _now_iso()

    if not api_key:
        return ToolResult(data=None, error="TAVILY_API_KEY not configured", retrievedAt=retrieved_at)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": validated.query,
                    "max_results": validated.max_results,
                    "search_depth": "advanced",
                },
            )
        if resp.status_code != 200:
            return ToolResult(
                data=None,
                error=f"Tavily {resp.status_code}: {resp.reason_phrase}",
                retrievedAt=retrieved_at,
            )

        raw = resp.json()
        return ToolResult(
            data={
                "results": [
                    {
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "excerpt": r.get("content"),
                        "publishedAt": r.get("published_date"),
                    }
                    for r in raw.get("results", [])
                ],
                "totalFound": len(raw.get("results", [])),
            },
            sourceUrl=f"https://tavily.com/search?q={validated.query}",
            retrievedAt=retrieved_at,
        )
    except httpx.TimeoutException:
        return ToolResult(data=None, error="Tavily timed out after 10s", retrievedAt=retrieved_at)
    except Exception as e:
        return ToolResult(data=None, error=str(e), retrievedAt=retrieved_at)


class _WebSearchTool:
    name = "web_search"
    description = (
        "General web search via Tavily. Use only when no domain tool covers the query "
        "(recent news, market commentary). Do NOT use for ISO form language, regulatory "
        "filings, or carrier ratings."
    )
    input_schema = _INPUT_SCHEMA
    output_schema = _OUTPUT_SCHEMA
    cache_ttl_seconds = 900
    estimated_cost_usd = 0.002
    vertical = "insurance"

    async def call(self, input_: dict[str, Any]) -> ToolResult:
        return await _call(input_)


web_search_tool = _WebSearchTool()
