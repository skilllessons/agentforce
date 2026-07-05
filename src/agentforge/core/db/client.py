"""Async Postgres pool singleton (asyncpg).

One lazily-created connection pool per process. Repos call :func:`get_pool`
and acquire individual connections via ``async with pool.acquire() as conn``.
Mirrors the singleton pattern used by :mod:`agentforge.core.tools.redis_client`.

Why a pool: opening a Postgres connection costs ~50-100ms (TCP + auth +
session setup). A pool keeps N connections warm; per-query cost drops to
~1ms acquire + the actual query.

Why a singleton: one shared pool per process is the standard pattern. If
every request opened its own pool we'd quickly exhaust Postgres's
``max_connections`` (default 100).
"""

from __future__ import annotations

import asyncpg

from agentforge.core.config import get_settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the process-wide asyncpg pool, creating it on first call."""
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=1,
        max_size=10,
        command_timeout=30,
    )
    if _pool is None:
        raise RuntimeError("Failed to create asyncpg pool")
    return _pool


async def close_db() -> None:
    """Tear down the pool. Call from app shutdown handlers and test teardown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
