"""run_events table — append + list_for_run.

The append-only audit trail of everything that happened in a run
(tool_start, tool_result, synthesis_start, output, stop, error). Durable
mirror of the Redis pub/sub stream: a client that disconnects mid-run can
replay it, and we can debug a run after the fact.
"""

from __future__ import annotations

import json
from typing import Any

from agentforge.core.db.client import get_pool


async def append(
    run_id: str,
    *,
    tenant_id: str,
    kind: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append one event row. `id` and `created_at` are DB-assigned."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO run_events (run_id, tenant_id, kind, payload)
            VALUES ($1, $2, $3, $4::jsonb)
            """,
            run_id,
            tenant_id,
            kind,
            json.dumps(payload or {}),
        )


async def list_for_run(run_id: str) -> list[dict[str, Any]]:
    """Return all events for a run in chronological order (by BIGSERIAL id)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM run_events WHERE run_id = $1 ORDER BY id",
            run_id,
        )
        return [dict(r) for r in rows]
