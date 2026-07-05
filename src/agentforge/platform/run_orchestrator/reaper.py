"""Stuck-run reaper — recover runs orphaned by crashed workers.

runs.reclaim_stuck() flips stuck 'running' runs back to 'queued' (transient
crash) or 'failed' (poison run, over the attempt cap) in Postgres. But a
re-queued row is invisible to workers until its id is back on the Redis queue —
so this re-LPUSHes the requeued ones onto their PER-VERTICAL queue (that's why
reclaim_stuck RETURNs vertical).

Runs as a one-shot sweep (`agentforge-reap`). In K8s it's a CronJob every
1-2 minutes; locally you run it by hand.
"""

from __future__ import annotations

import asyncio
from typing import Any

from dotenv import load_dotenv

from agentforge.core.db.client import close_db
from agentforge.core.db.repos import runs
from agentforge.core.observability import configure_logging, get_logger
from agentforge.core.tools.redis_client import close_redis, get_redis
from agentforge.platform.run_orchestrator.keys import queue_key

log = get_logger("reaper")

_STUCK_AFTER_SECONDS = 120
_MAX_ATTEMPTS = 3


async def reap_once(
    *,
    older_than_seconds: int = _STUCK_AFTER_SECONDS,
    max_attempts: int = _MAX_ATTEMPTS,
) -> dict[str, Any]:
    """One sweep: reclaim stuck runs, re-queue the recoverable ones."""
    res = await runs.reclaim_stuck(
        older_than_seconds=older_than_seconds, max_attempts=max_attempts
    )
    redis = get_redis()
    for run_id, vertical in res["requeued"]:
        await redis.lpush(queue_key(vertical), run_id)

    if res["requeued"] or res["failed"]:
        log.info(
            "reaper.swept",
            requeued=len(res["requeued"]),
            dead_lettered=len(res["failed"]),
        )
    return res


async def _main() -> None:
    load_dotenv()
    configure_logging()
    try:
        await reap_once()
    finally:
        await close_db()
        await close_redis()


def cli() -> None:
    """Console-script entry point (agentforge-reap). One-shot sweep."""
    asyncio.run(_main())


if __name__ == "__main__":
    cli()
