"""Shared pytest fixtures.

The agent runtime touches Redis via ``with_cache``; we monkey-patch the
``get_redis`` factory in unit tests to a tiny in-memory fake so tests don't
require a running Redis.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self._store[key] = value

    async def aclose(self) -> None:
        return None


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeRedis]:
    fake = _FakeRedis()
    from agentforge.core.tools import redis_client

    monkeypatch.setattr(redis_client, "_client", fake)
    monkeypatch.setattr(redis_client, "get_redis", lambda: fake)
    # Also patch the cache module's bound reference (it imported get_redis at module load).
    from agentforge.core.tools import cache

    monkeypatch.setattr(cache, "get_redis", lambda: fake)
    yield fake
    monkeypatch.setattr(redis_client, "_client", None)


@pytest.fixture
def env_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tests don't accidentally hit live LLMs."""
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LITELLM_API_BASE", "TAVILY_API_KEY"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def fixture_env(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Set deterministic envs for tests that need them."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    return monkeypatch
