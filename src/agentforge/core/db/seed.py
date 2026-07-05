"""Seed the local-dev tenant.

runs.tenant_id is an FK to tenants(id), so a run can't be inserted until its
tenant exists. The CLI defaults --tenant to "local-dev"; this creates it.
Idempotent (upsert), safe to re-run.
"""

from __future__ import annotations

import asyncio

from agentforge.core.db.client import close_db
from agentforge.core.db.repos import tenants


async def _seed() -> None:
    await tenants.upsert("local-dev", name="Local Dev", email=None)
    print("✓ seeded tenant: local-dev")


async def _main() -> None:
    try:
        await _seed()
    finally:
        await close_db()


def cli() -> None:
    """Console-script entry point (agentforge-seed)."""
    asyncio.run(_main())


if __name__ == "__main__":
    cli()
