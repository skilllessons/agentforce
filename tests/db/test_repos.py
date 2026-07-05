"""Round-trip smoke test against a real local Postgres.

Skipped automatically when Postgres isn't reachable so unit-test runs stay
fast and zero-dependency. Bring the DB up first with::

    bash scripts/bootstrap-local.sh

then::

    uv run pytest tests/db/ -q
"""

from __future__ import annotations

import time

import asyncpg
import pytest

from agentforge.core.config import get_settings
from agentforge.core.db.client import close_db, get_pool
from agentforge.core.db.migrate import run_migrations
from agentforge.core.db.repos import runs, tenants


async def _postgres_reachable() -> bool:
    try:
        conn = await asyncpg.connect(get_settings().database_url, timeout=2)
    except (OSError, asyncpg.PostgresError, TimeoutError):
        return False
    await conn.close()
    return True


@pytest.fixture(autouse=True)
async def _require_postgres() -> None:
    if not await _postgres_reachable():
        pytest.skip("local Postgres not running — run scripts/bootstrap-local.sh")


@pytest.fixture(scope="session")
async def _migrated() -> None:
    """Apply migrations once per session before any repo test runs."""
    if not await _postgres_reachable():
        return
    await run_migrations()


@pytest.fixture(autouse=True)
async def _pool_teardown() -> None:
    yield
    await close_db()


@pytest.mark.asyncio
async def test_tenant_upsert_and_get(_migrated: None) -> None:
    tenant_id = f"test-{int(time.time() * 1000)}"

    await tenants.upsert(tenant_id, name="Test Tenant", email="t@example.com")
    row = await tenants.get(tenant_id)

    assert row is not None
    assert row["id"] == tenant_id
    assert row["name"] == "Test Tenant"
    assert row["email"] == "t@example.com"
    assert row["status"] == "active"

    # upsert again with a new name — should update, not duplicate
    await tenants.upsert(tenant_id, name="Renamed", email=None)
    row2 = await tenants.get(tenant_id)
    assert row2 is not None
    assert row2["name"] == "Renamed"
    assert row2["email"] is None


@pytest.mark.asyncio
async def test_run_lifecycle_completed(_migrated: None) -> None:
    ts = int(time.time() * 1000)
    tenant_id = f"test-{ts}"
    run_id = f"run_{ts}_ok"

    await tenants.upsert(tenant_id, name="Test")
    await runs.insert_queued(
        run_id,
        tenant_id=tenant_id,
        vertical="insurance",
        query="What does MDL-880 say?",
        limits={"max_steps": 8},
    )

    queued = await runs.get(run_id)
    assert queued is not None
    assert queued["status"] == "queued"
    assert queued["vertical"] == "insurance"
    assert queued["attempt_count"] == 0

    await runs.mark_running(run_id)
    running = await runs.get(run_id)
    assert running is not None
    assert running["status"] == "running"
    assert running["started_at"] is not None
    assert running["attempt_count"] == 1

    await runs.mark_completed(
        run_id,
        result={"summary": "ok", "findings": [], "sources": [], "flags": []},
        cost_usd=0.0123,
        tool_call_count=3,
        elapsed_seconds=4.5,
    )
    done = await runs.get(run_id)
    assert done is not None
    assert done["status"] == "completed"
    assert done["completed_at"] is not None
    assert done["tool_call_count"] == 3
    assert float(done["cost_usd"]) == pytest.approx(0.0123, abs=1e-6)
    assert done["result"] is not None  # JSONB returned as str or dict by asyncpg


@pytest.mark.asyncio
async def test_run_lifecycle_failed(_migrated: None) -> None:
    ts = int(time.time() * 1000)
    tenant_id = f"test-{ts}"
    run_id = f"run_{ts}_fail"

    await tenants.upsert(tenant_id, name="Test")
    await runs.insert_queued(
        run_id,
        tenant_id=tenant_id,
        vertical="insurance",
        query="will fail",
    )
    await runs.mark_running(run_id)
    await runs.mark_failed(run_id, "synthesis returned non-JSON")

    failed = await runs.get(run_id)
    assert failed is not None
    assert failed["status"] == "failed"
    assert failed["last_error"] == "synthesis returned non-JSON"
    assert failed["completed_at"] is not None
