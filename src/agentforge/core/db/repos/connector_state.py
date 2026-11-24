"""Connector resume cursors — read and save.

One row per changelog, keyed (tenant_id, source, resource). A poller is a
CronJob: it starts, drains, exits. Without this the cursor dies with the
process and every run re-fetches the source's entire history.
"""

from __future__ import annotations

from agentforge.core.db.client import get_pool

_SAVE = """
INSERT INTO connector_state (tenant_id, source, resource, cursor)
VALUES ($1, $2, $3, $4)
ON CONFLICT (tenant_id, source, resource) DO UPDATE
  SET cursor = COALESCE(EXCLUDED.cursor, connector_state.cursor),
      updated_at = NOW()
"""


async def get(tenant_id: str, source: str, resource: str) -> str | None:
    """The cursor to resume from, or None to backfill.

    None covers both "no row yet" and "row with a NULL cursor". The caller
    treats them identically — neither gives a position to resume from.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT cursor FROM connector_state"
            " WHERE tenant_id = $1 AND source = $2 AND resource = $3",
            tenant_id,
            source,
            resource,
        )


async def save(tenant_id: str, source: str, resource: str, cursor: str | None) -> None:
    """Record the position after a page. Called per page, not per run.

    A NULL cursor never erases a stored one — the COALESCE keeps the existing
    value. Zendesk sends ``after_cursor: null`` on an empty page, and treating
    that as "clear the position" would force a full re-backfill every poll.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(_SAVE, tenant_id, source, resource, cursor)
