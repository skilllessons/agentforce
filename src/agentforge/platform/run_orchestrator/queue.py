"""Run queue — enqueue (accept) and dequeue (worker pulls).

Design rules to keep in mind while filling these in:
  - enqueue writes the durable Postgres row FIRST, then pushes to Redis.
    Fail-safe order: a row with no queue entry just sits as 'queued'
    (recoverable); a queue entry with no row would crash the worker.
  - LPUSH + BRPOP gives FIFO with a blocking pull (no busy-polling).
"""

from __future__ import annotations

from typing import Any

from agentforge.core.db.repos import runs
from agentforge.core.tools.redis_client import get_redis
from agentforge.platform.run_orchestrator.keys import queue_key


async def enqueue_run(
    run_id: str,
    *,
    tenant_id: str,
    vertical: str,
    query: str,
    context: dict[str, Any] | None = None,
    limits: dict[str, Any] | None = None,
) -> None:
    await runs.insert_queued(run_id= run_id, tenant_id= tenant_id, vertical=vertical,
                             query=query, context=context, limits=limits)
    redis = get_redis()
    await redis.lpush(queue_key(vertical), run_id)


async def dequeue_run(vertical: str, timeout: int = 5) -> str | None:
    """Block up to `timeout` seconds for the next run id. None on timeout."""
    redis = get_redis()
    result = await redis.brpop(queue_key(vertical), timeout=timeout)
    if result is None:
        return None
    _key, run_id = result  # brpop returns (key, value)
    return run_id
