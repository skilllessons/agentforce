"""api_keys table — insert + lookup by hash.

Keys are stored hashed (sha256 hex), never in plaintext — same discipline as
passwords. Verification hashes the presented key and looks up the row,
resolving the tenant_id only if the key is LIVE (not revoked, not expired).
"""

from __future__ import annotations

from agentforge.core.db.client import get_pool


async def insert(
    *,
    tenant_id: str,
    key_hash: str,
    key_prefix: str,
    name: str | None = None,
) -> None:
    """Store a new key's hash + prefix. The plaintext key is never persisted."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO api_keys (tenant_id, key_hash, key_prefix, name)
            VALUES ($1, $2, $3, $4)
            """,
            tenant_id,
            key_hash,
            key_prefix,
            name,
        )


async def lookup_tenant_by_hash(key_hash: str) -> str | None:
    """Return the tenant_id for a LIVE key, or None if missing/revoked/expired."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            SELECT tenant_id
              FROM api_keys
             WHERE key_hash = $1
               AND revoked_at IS NULL
               AND (expires_at IS NULL OR expires_at > NOW())
            """,
            key_hash,
        )
