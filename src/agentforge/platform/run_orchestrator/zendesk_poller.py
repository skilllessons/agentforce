"""Zendesk ticket poller — one-shot, CronJob-shaped like the reaper.

Reads the resume cursor, drains everything Zendesk has changed since, writes it
to `tickets`, and records the new position. Exits.

A poller rather than a webhook because a webhook needs public ingress before
anything works at all — a tunnel on a laptop or a deployed cluster. The webhook
can come later; it is a route and a signature check.
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from agentforge.connectors.zendesk.client import ZendeskClient
from agentforge.connectors.zendesk.mapping import to_ticket_row
from agentforge.core.db.client import close_db
from agentforge.core.db.repos import connector_state, tickets
from agentforge.core.observability import configure_logging, get_logger

log = get_logger("zendesk.poller")

SOURCE = "zendesk"
RESOURCE = "tickets"


async def poll_once(tenant_id: str = "local-dev") -> int:
    """Drain Zendesk's ticket changelog into Postgres. Returns tickets written.

    Ordering within a page is the only real decision here: tickets first, then
    the cursor. A crash between the two re-processes one page, which the upsert
    absorbs. The reverse order would skip those tickets permanently — losing
    duplicates is recoverable, losing data is not.

    The cursor is saved per page, not at the end of the run, so a crash
    mid-backfill keeps its progress. It is saved even when a page is empty,
    because Zendesk advances the cursor regardless; skipping that would
    re-scan the same window forever.
    """
    cursor = await connector_state.get(tenant_id, SOURCE, RESOURCE)
    log.info("poll.start", tenant=tenant_id, resuming=cursor is not None)

    written = 0
    async with ZendeskClient() as zd:
        async for batch, after in zd.iter_tickets(cursor):
            for ticket in batch:
                await tickets.upsert(to_ticket_row(ticket, tenant_id))
                written += 1
            await connector_state.save(tenant_id, SOURCE, RESOURCE, after)
            log.info("poll.page", tickets=len(batch))

    log.info("poll.done", written=written)
    return written


async def _main() -> None:
    load_dotenv()
    configure_logging()
    try:
        await poll_once()
    finally:
        await close_db()


def cli() -> None:
    """Console-script entry point (agentforge-poll-zendesk). One-shot drain."""
    asyncio.run(_main())


if __name__ == "__main__":
    cli()
