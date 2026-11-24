"""Load the captured Zendesk fixture into `tickets` — dev only.

The Zendesk trial expired 2026-10-24, so the poller has no live source to drain.
This replaces it: the same seven real tickets, mapped through the same
`to_ticket_row` and written by the same `tickets.upsert`, straight from the
verbatim payload recorded in the test fixture.

Lives in `scripts/` rather than `src/` because it reads from `tests/`. Neither
directory ships in the wheel, so that dependency is fine here and would not be
inside the package. Consequently there is no console-script entry point — run it
as `uv run python scripts/seed_tickets.py`.

Requires the `local-dev` tenant to exist first (`tickets.tenant_id` is an FK):

    uv run agentforge-seed
    uv run python scripts/seed_tickets.py
"""
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from agentforge.connectors.zendesk.mapping import to_ticket_row
from agentforge.core.db import close_db
from agentforge.core.db.repos import tenants, tickets
from agentforge.core.observability import configure_logging

# Resolved from __file__, not the cwd, so the script runs from anywhere.
_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "connectors"
    / "fixtures"
    / "zendesk_tickets.json"
)
_SUPPORT_FIXTURE = (
    Path(__file__).resolve().parents[1] / "tests" / "support" / "fixtures" / "support_tickets.json"
)


async def seed_tickets(tenant_id: str = "local-dev") -> int:
    """Upsert every ticket in the fixture. Returns the number written.

    Each ticket goes through the same `to_ticket_row` and `tickets.upsert` the
    poller uses, so this exercises the real mapping and the real SQL.

    The fixture's other top-level keys — `next_page`, `previous_page`, `count` —
    are artifacts of the non-incremental endpoint and are not used.

    Re-running is harmless: the upsert keys on (tenant_id, source, external_id),
    so a second pass updates the same seven rows rather than inserting more.
    """
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    for ticket in payload["tickets"]:
        await tickets.upsert(to_ticket_row(ticket, tenant_id))
    return len(payload["tickets"])


async def seed_support_tickets() -> dict[str, int]:
    """Upsert the hand-written support tickets, per tenant. Returns {tenant_id: count}.

    Creates each tenant first (tickets.tenant_id is an FK). `acme-test` exists
    only so tests can prove one tenant's search never returns another's tickets.
    """
    payload = json.loads(_SUPPORT_FIXTURE.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for tenant_id, rows in payload["tenants"].items():
        if await tenants.get(tenant_id) is None:
            await tenants.upsert(tenant_id, name=tenant_id, email=None)
        for ticket in rows:
            await tickets.upsert(to_ticket_row(ticket, tenant_id))
        counts[tenant_id] = len(rows)
    return counts


async def _main() -> None:
    load_dotenv()
    configure_logging()
    try:
        written = await seed_tickets()
        print(f"✓ seeded {written} ticket(s) from {_FIXTURE.name}")
        for tenant_id, n in (await seed_support_tickets()).items():
            print(f"✓ seeded {n} ticket(s) for {tenant_id} from {_SUPPORT_FIXTURE.name}")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(_main())
