"""Redis-backed result cache for tool calls.

Cache reads + writes are best-effort; a failure here MUST NOT break the agent
loop (the live API call is the source of truth, the cache is an optimization).
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from agentforge.core.tools.protocol import ResearchTool, ToolResult
from agentforge.core.tools.redis_client import get_redis

log = logging.getLogger(__name__)


def hash_input(input_: Any) -> str:
    payload = json.dumps(input_, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


async def with_cache(
    tool: ResearchTool,
    input_: dict[str, Any],
    fn: Callable[[], Awaitable[ToolResult]],
    *,
    tenant_id: str | None = None,
) -> ToolResult:
    if tool.cache_ttl_seconds == 0:
        return await fn()

    namespace = f"tenant:{tenant_id}:" if tenant_id else ""
    key = f"{namespace}tool:{tool.name}:{hash_input(input_)}"
    redis = get_redis()

    try:
        cached = await redis.get(key)
        if cached:
            payload = json.loads(cached)
            payload["fromCache"] = True
            return ToolResult.model_validate(payload)
    except Exception as e:
        log.warning("cache read failed: %s", e)

    result = await fn()

    if result.success:
        try:
            await redis.setex(
                key,
                tool.cache_ttl_seconds,
                json.dumps(result.model_dump(by_alias=True, exclude_none=True), default=str),
            )
        except Exception as e:
            log.warning("cache write failed: %s", e)
    return result
