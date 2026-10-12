"""Tickets table — upsert from a connector.

The connector is the only writer. It re-sends every ticket it sees, including
ones already stored, because an incremental export can replay a record and
because a changed ticket arrives as the same record with new values. So the
write has to be idempotent: ``ON CONFLICT (tenant_id, source, external_id)``
turns the second arrival into an update of the first row rather than a
duplicate.
"""

from __future__ import annotations

import json
from typing import Any

from nanoid import generate as nanoid

from agentforge.core.db.client import get_pool

_UPSERT = """
INSERT INTO tickets (
    id, tenant_id, source, external_id, subject, body,
    requester_person_id, assignee_person_id, status, priority, tags,
    group_external_id, external_created_at, external_updated_at, raw
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
ON CONFLICT (tenant_id, source, external_id) DO UPDATE SET
    subject             = EXCLUDED.subject,
    body                = EXCLUDED.body,
    status              = EXCLUDED.status,
    priority            = EXCLUDED.priority,
    tags                = EXCLUDED.tags,
    group_external_id   = EXCLUDED.group_external_id,
    external_created_at = EXCLUDED.external_created_at,
    external_updated_at = EXCLUDED.external_updated_at,
    raw                 = EXCLUDED.raw,
    synced_at           = NOW(),
    -- COALESCE, not assignment: the connector sends NULL for these until
    -- persons is populated, and a plain overwrite would erase links that
    -- something else set.
    requester_person_id = COALESCE(EXCLUDED.requester_person_id, tickets.requester_person_id),
    assignee_person_id  = COALESCE(EXCLUDED.assignee_person_id,  tickets.assignee_person_id)
RETURNING id
"""


async def upsert(row: dict[str, Any]) -> str:
    """Insert or refresh one ticket. Returns its id.

    ``row`` is what ``connectors.zendesk.mapping.to_ticket_row`` produces: every
    column except the primary key, which is minted here.

    On conflict the RETURNING clause yields the *existing* id, not the nanoid
    generated for this call — the row keeps the identity it was created with,
    so anything already referencing it stays valid.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            _UPSERT,
            nanoid(size=12),
            row["tenant_id"],
            row["source"],
            row["external_id"],
            row["subject"],
            row["body"],
            row["requester_person_id"],
            row["assignee_person_id"],
            row["status"],
            row["priority"],
            row["tags"],
            row["group_external_id"],
            row["external_created_at"],
            row["external_updated_at"],
            # asyncpg binds a dict as a composite type, not jsonb.
            json.dumps(row["raw"]),
        )
