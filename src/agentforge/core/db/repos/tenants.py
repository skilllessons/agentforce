"""Tenants table — get + upsert.

Tenant ids are the same string baked into API keys (``af_<tenantId>_<sig>``).
The bootstrap script seeds a ``local-dev`` tenant; the admin onboarding flow
will add real ones later.
"""

from __future__ import annotations

from typing import Any

from agentforge.core.db.client import get_pool


async def get(tenant_id: str) -> dict[str, Any] | None:
    """Return tenant row as dict, or None if absent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tenants WHERE id = $1",
            tenant_id,
        )
        return dict(row) if row else None


async def upsert(
    tenant_id: str,
    name: str,
    email: str | None = None,
) -> None:
    """Insert a tenant, or update name/email if it already exists."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tenants (id, name, email)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE
              SET name = EXCLUDED.name,
                  email = EXCLUDED.email
            """,
            tenant_id,
            name,
            email,
        )
