"""Apply SQL migrations from ``infra/postgres/migrations/`` to Postgres.

Tiny home-grown migrator — we write raw SQL, not ORM models, so Alembic
buys us nothing. Each ``.sql`` file is applied inside its own transaction
and recorded in a ``schema_migrations`` tracking table so re-runs are
idempotent.

Usage:
    from agentforge.core.db.migrate import run_migrations
    await run_migrations()

Or from the shell:
    uv run python -m agentforge.core.db.migrate
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from agentforge.core.db.client import close_db, get_pool

# infra/postgres/migrations lives at the repo root, four parents up from this
# file: db/ -> core/ -> agentforge/ -> src/ -> <repo>
_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[4] / "infra" / "postgres" / "migrations"
)

_TRACKING_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename     TEXT PRIMARY KEY,
    applied_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def run_migrations(migrations_dir: Path | None = None) -> list[str]:
    """Apply any new ``.sql`` files in sorted order. Returns names applied."""
    directory = migrations_dir or _MIGRATIONS_DIR
    if not directory.is_dir():
        raise FileNotFoundError(f"migrations dir not found: {directory}")

    files = sorted(p for p in directory.iterdir() if p.suffix == ".sql")
    pool = await get_pool()
    applied: list[str] = []

    async with pool.acquire() as conn:
        await conn.execute(_TRACKING_TABLE_DDL)
        already = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM schema_migrations")
        }

        for path in files:
            if path.name in already:
                continue
            sql = path.read_text(encoding="utf-8")
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)",
                    path.name,
                )
            applied.append(path.name)
            print(f"  applied {path.name}")

    return applied


async def _main() -> None:
    try:
        names = await run_migrations()
        if not names:
            print("✓ no new migrations")
        else:
            print(f"✓ applied {len(names)} migration(s)")
    finally:
        await close_db()


def cli() -> None:
    """Console-script entry point (agentforge-migrate)."""
    asyncio.run(_main())


if __name__ == "__main__":
    cli()
