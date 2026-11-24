"""ticket_search — behavior + tenant isolation, against a real local Postgres.

Skipped automatically when Postgres isn't reachable (same as tests/db/).
Data: tests/support/fixtures/support_tickets.json, upserted once per session
for two tenants — local-dev (25 tickets, ids 101-125) and acme-test (4 tickets,
ids 9001-9004). Upsert is idempotent, so re-running against a seeded DB is safe.

The tool is called directly (ticket_search_tool.call), which bypasses with_cache,
so no Redis is needed.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import asyncpg
import pytest

from agentforge.connectors.zendesk.mapping import to_ticket_row
from agentforge.core.config import get_settings
from agentforge.core.db.client import close_db
from agentforge.core.db.migrate import run_migrations
from agentforge.core.db.repos import tenants, tickets
from agentforge.core.runtime.tenant import current_tenant
from agentforge.verticals.support.tools import ticket_search as mod
from agentforge.verticals.support.tools.ticket_search import ticket_search_tool

_FIXTURE = Path(__file__).parent / "fixtures" / "support_tickets.json"



# ── fixtures (scaffolding — no need to change) ──────────────────────────────


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
async def seeded() -> None:
    """Migrate, then upsert both tenants and their tickets once per session."""
    if not await _postgres_reachable():
        return
    await run_migrations()
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    for tenant_id, rows in payload["tenants"].items():
        if await tenants.get(tenant_id) is None:
            await tenants.upsert(tenant_id, name=tenant_id, email=None)
        for ticket in rows:
            await tickets.upsert(to_ticket_row(ticket, tenant_id))


@pytest.fixture(autouse=True)
async def _pool_teardown() -> AsyncIterator[None]:
    yield
    await close_db()


@pytest.fixture
def as_tenant() -> Any:
    """Call as_tenant("local-dev") inside a test to set the run's tenant.

    No reset needed: each async test runs in its own task with a copy of the
    context, so the value dies with the test.
    """

    def _set(tenant_id: str) -> None:
        current_tenant.set(tenant_id)

    return _set


def _ids(result: Any) -> set[str]:
    """Ticket ids from a successful ToolResult, as a set (order-independent)."""
    return {t["ticketId"] for t in result.data["tickets"]}


# ── tests (YOU write the bodies) ────────────────────────────────────────────
# Each test: arrange (as_tenant), act (await ticket_search_tool.call({...})),
# assert. Delete the `raise NotImplementedError` once the asserts are in.


async def test_match_returns_tickets_with_citable_fields(seeded: None, as_tenant: Any) -> None:
    as_tenant("local-dev")
    result = await ticket_search_tool.call({"query": "refund"})
    assert result.success
    assert "101" in _ids(result)
    keys = {"ticketId", "subject", "snippet", "status", "priority", "createdAt", "url"}
    for t in result.data["tickets"]:
        assert set(t) == keys


async def test_status_filter_reaches_the_query(seeded: None, as_tenant: Any) -> None:
    as_tenant("local-dev")
    open_ = await ticket_search_tool.call({"query": "billing", "status": "open"})
    solved = await ticket_search_tool.call({"query": "billing", "status": "solved"})
    assert all(t["status"] == "open" for t in open_.data["tickets"])
    assert "104" in _ids(solved)
    assert "104" not in _ids(open_)


async def test_no_match_is_success_with_notice(seeded: None, as_tenant: Any) -> None:
    as_tenant("local-dev")
    result = await ticket_search_tool.call({"query": "zebra"})
    assert result.success is True
    assert result.error is None
    assert result.data["tickets"] == []
    assert "notice" in result.data


async def test_db_error_returns_error_not_raise(
    seeded: None, as_tenant: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("db down")

    monkeypatch.setattr(mod.tickets, "search", boom)
    as_tenant("local-dev")
    result = await ticket_search_tool.call({"query": "refund"})
    assert result.data is None
    assert result.error is not None
    assert "ticket search failed" in result.error


async def test_no_tenant_refuses_before_querying(
    seeded: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []

    async def spy(*args: Any, **kwargs: Any) -> Any:
        calls.append(args)
        return []

    monkeypatch.setattr(mod.tickets, "search", spy)
    result = await ticket_search_tool.call({"query": "refund"})
    assert result.error == "no tenant in context"
    assert result.data is None
    assert calls == []


async def test_tenants_never_see_each_others_tickets(seeded: None, as_tenant: Any) -> None:
    q = {"query": "login OR billing OR refund OR export", "limit": 20}
    acme = {"9001", "9002", "9003", "9004"}

    as_tenant("local-dev")
    local = _ids(await ticket_search_tool.call(q))
    assert local
    assert not (local & acme)

    as_tenant("acme-test")
    theirs = _ids(await ticket_search_tool.call(q))
    assert theirs
    assert theirs <= acme

async def test_multi_word_query_matches_any_word(seeded: None, as_tenant: Any) -> None:
    # Regression: "credit card declined" used to require all 3 words and missed #103.
    as_tenant("local-dev")
    result = await ticket_search_tool.call({"query": "credit card declined"})
    assert "103" in _ids(result)


def test_cache_ttl_is_zero() -> None:
    assert ticket_search_tool.cache_ttl_seconds == 0
