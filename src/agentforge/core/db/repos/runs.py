"""Runs lifecycle — insert_queued / mark_running / mark_completed / mark_failed.

Four explicit transitions instead of a generic ``update_run(**kwargs)`` helper.
This makes the state machine grep-able: every place a run changes status is
a ``mark_*`` call.

State machine:
    queued → running → completed
                    ↘ failed
"""

from __future__ import annotations

import json
from typing import Any

from agentforge.core.db.client import get_pool


async def insert_queued(
    run_id: str,
    *,
    tenant_id: str,
    vertical: str,
    query: str,
    context: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    limits: dict[str, Any] | None = None,
    webhook_url: str | None = None,
) -> None:
    """Insert a fresh queued run. Called BEFORE pushing the id onto Redis."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO runs (
                id, tenant_id, vertical, query,
                context, attachments, limits, webhook_url
            )
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8)
            """,
            run_id,
            tenant_id,
            vertical,
            query,
            json.dumps(context or {}),
            json.dumps(attachments or []),
            json.dumps(limits or {}),
            webhook_url,
        )


async def mark_running(run_id: str) -> bool:
    """Transition queued → running. Worker calls this on dequeue."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE runs
               SET status = 'running',
                   started_at = NOW(),
                   attempt_count = attempt_count + 1
             WHERE id = $1 AND status = 'queued'
             RETURNING id
            """,
            run_id,
        )

        if row is not None:
            return True
        return False


async def mark_completed(
    run_id: str,
    *,
    result: dict[str, Any],
    cost_usd: float,
    tool_call_count: int,
    elapsed_seconds: float,
) -> None:
    """Transition running → completed and store the ResearchOutput body."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE runs
               SET status = 'completed',
                   result = $2::jsonb,
                   cost_usd = $3,
                   tool_call_count = $4,
                   elapsed_seconds = $5,
                   completed_at = NOW()
             WHERE id = $1
            """,
            run_id,
            json.dumps(result),
            cost_usd,
            tool_call_count,
            elapsed_seconds,
        )


async def mark_failed(run_id: str, error: str) -> None:
    """Transition running → failed. Stores last_error and stamps completed_at."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE runs
               SET status = 'failed',
                   last_error = $2,
                   completed_at = NOW()
             WHERE id = $1
            """,
            run_id,
            error,
        )

async def reclaim_stuck(*, older_than_seconds: int, max_attempts: int) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            rows1 = await conn.fetch(
                """
                  UPDATE runs SET status='queued'
                    WHERE status='running'
                    AND started_at < NOW() - make_interval(secs => $1)
                    AND attempt_count < $2
                  RETURNING id, vertical
                """,
                older_than_seconds,  # $1
                max_attempts,  # $2
            )

            rows2 = await conn.fetch(
                """
                  UPDATE runs SET status='failed',
                  last_error='reaped: exceeded max attempts', completed_at=NOW()
                    WHERE status='running'
                    AND started_at < NOW() - make_interval(secs => $1)
                    AND attempt_count >= $2
                  RETURNING id
                """,
                older_than_seconds,  # $1
                max_attempts,  # $2
            )

        return {"requeued": [(r["id"], r["vertical"]) for r in rows1], "failed": [r["id"] for r in rows2]}



async def get(run_id: str) -> dict[str, Any] | None:
    """Fetch one run by id. Returns None if missing."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM runs WHERE id = $1", run_id)
        return dict(row) if row else None
