"""sessions table — conversation threads that group runs for multi-turn context."""

from __future__ import annotations

from typing import Any

from agentforge.core.db.client import get_pool


async def create(session_id: str, *, tenant_id: str, vertical: str, title: str | None = None) -> None:
    """Open a new conversation thread."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (id, tenant_id, vertical, title)
            VALUES ($1, $2, $3, $4)
            """,
            session_id,
            tenant_id,
            vertical,
            title,
        )


async def list_recent(tenant_id: str, *, limit: int = 30) -> list[dict[str, Any]]:
    """Recent threads for the sidebar, newest activity first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, vertical, title, created_at, updated_at
              FROM sessions
             WHERE tenant_id = $1
             ORDER BY updated_at DESC
             LIMIT $2
            """,
            tenant_id,
            limit,
        )
        return [dict(r) for r in rows]


async def touch(session_id: str, *, title: str | None = None) -> None:
    """Bump updated_at (rises in the sidebar); set the title if not already set."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE sessions
               SET updated_at = NOW(),
                   title = COALESCE(title, $2)
             WHERE id = $1
            """,
            session_id,
            title,
        )
