"""Async Redis singleton."""

from __future__ import annotations

import os

from redis.asyncio import Redis

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is not None:
        return _client
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    _client = Redis.from_url(url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
