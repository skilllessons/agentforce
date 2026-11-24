"""ticket_search — keyword search over the tenant's own support tickets.

Source: our Postgres `tickets` table (ingested by the Zendesk connector). Status: live.
Keyword matching only (Postgres full-text); pgvector hybrid retrieval lands in M3
behind the same `tickets.search` signature.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agentforge.core.config import get_settings
from agentforge.core.db.repos import tickets
from agentforge.core.runtime.tenant import get_tenant
from agentforge.core.tools.protocol import ToolResult
from agentforge.core.tools.validate import validate_input

_STATUS = Literal["new", "open", "pending", "hold", "solved", "closed"]


class _Input(BaseModel):
    # Mirrors "additionalProperties": False — reject, don't silently drop, unknown keys.
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    status: _STATUS | None = None
    limit: int = Field(default=5, ge=1, le=20)


_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "minLength": 1,
            "description": "Keywords to search for in ticket subject and first message.",
        },
        "status": {
            "type": "string",
            "enum": ["new", "open", "pending", "hold", "solved", "closed"],
        },
        "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
    },
    "required": ["query"],
    "additionalProperties": False,
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"tickets": {"type": "array"}, "notice": {"type": "string"}},
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _call(input_: dict[str, Any]) -> ToolResult:
    try:
        q = validate_input(input_, _Input)
    except Exception as e:
        return ToolResult(data=None, error=str(e), retrievedAt=_now_iso())

    # The tenant comes from the run, never from the model. No tenant → no query.
    tenant = get_tenant()
    if tenant is None:
        return ToolResult(data=None, error="no tenant in context", retrievedAt=_now_iso())

    try:
        rows = await tickets.search(tenant, q.query, q.status, q.limit)
        if not rows:
            return ToolResult(
                data={"tickets": [], "notice": f"no tickets matched '{q.query}'"},
                retrievedAt=_now_iso(),
            )

        subdomain = get_settings().zendesk_subdomain
        found = [
            {
                "ticketId": r["external_id"],
                "subject": r["subject"],
                "snippet": (r["body"] or "")[:300],
                "status": r["status"],
                "priority": r["priority"],
                "createdAt": (
                    r["external_created_at"].isoformat() if r["external_created_at"] else None
                ),
                "url": (
                    f"https://{subdomain}.zendesk.com/agent/tickets/{r['external_id']}"
                    if subdomain
                    else None
                ),
            }
            for r in rows
        ]
        now = _now_iso()
        return ToolResult(
            data={"tickets": found},
            sourceUrl=found[0]["url"],
            retrievedAt=now,
        )
    except Exception as e:
        return ToolResult(data=None, error=f"ticket search failed: {e}", retrievedAt=_now_iso())


class _TicketSearchTool:
    name = "ticket_search"
    description = (
        "Searches this customer's own support tickets by keyword in the ticket subject and "
        "first message, and returns matching tickets with their IDs to cite. Use for any "
        "question about what customers report, complain about, or ask for. It matches words, "
        "not meaning: search several synonyms, e.g. 'refund', 'money back', 'charged twice'."
    )
    input_schema = _INPUT_SCHEMA
    output_schema = _OUTPUT_SCHEMA
    cache_ttl_seconds = 0
    estimated_cost_usd = 0.0
    vertical: str | None = "support"

    async def call(self, input_: dict[str, Any]) -> ToolResult:
        return await _call(input_)


ticket_search_tool = _TicketSearchTool()
