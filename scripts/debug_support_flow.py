"""Debug entry — step through the SUPPORT vertical with a SCRIPTED LLM.

Same idea as debug_flow.py (insurance): the router returns canned completions,
so it is free and deterministic. Everything else is the REAL code — enqueue ->
claim -> agent loop (tenant set) -> ticket_search -> tickets.search SQL ->
synthesis -> persist.

Postgres + Redis up, tickets seeded:  uv run python scripts/seed_tickets.py

STOP any running `agentforge-worker support` first. A live worker BRPOPs the
same queue, steals this run, and answers it with real Claude (real cost);
this script then times out and prints "done" for a run it never touched.

Breakpoints, in execution order:
  platform/worker/loop.py:82                    claim (mark_running)
  platform/worker/loop.py:88                    _load_vertical("support")
  platform/worker/loop.py:114                   into run_agent
  core/runtime/loop.py:82                       current_tenant.set
  core/runtime/loop.py:168                      tool.call(use.input)
  verticals/support/tools/ticket_search.py:68   get_tenant()
  verticals/support/tools/ticket_search.py:73   tickets.search(...)
  core/db/repos/tickets.py:106                  the SQL runs
  core/runtime/synthesize.py:46                 parse the model's JSON
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from agentforge.core.llm.types import (
    LLMCompletion,
    LLMTextBlock,
    LLMToolUseBlock,
    LLMUsage,
)
from agentforge.core.observability import configure_logging
from agentforge.core.tools.redis_client import get_redis
from agentforge.platform.run_orchestrator.keys import queue_key
from agentforge.platform.run_orchestrator.queue import enqueue_run
from agentforge.platform.worker.loop import process_one

_VERTICAL = "support"

_SYNTH_JSON = """{
  "summary": "Customers report double charges; one has escalated and threatens a chargeback.",
  "findings": [
    {
      "claim": "A customer has written three times about an unanswered double charge.",
      "evidence": "Ticket 123 says nobody answered two earlier tickets about the double charge.",
      "sourceRef": "123",
      "confidence": "high"
    }
  ],
  "sources": [
    {
      "id": "123",
      "title": "this is the third time I'm writing",
      "url": null,
      "retrievedAt": "2026-11-24T00:00:00Z",
      "dataVintage": "2026-11-08"
    }
  ],
  "flags": ["Ticket 123 threatens a bank chargeback."],
  "confidence": "medium"
}"""


class ScriptedRouter:
    """Returns a fixed sequence of completions across .complete() calls."""

    def __init__(self, completions: list[LLMCompletion]) -> None:
        self._queue = completions

    def supports_multimodal(self) -> bool:
        return True

    async def complete(self, **kwargs: Any) -> LLMCompletion:
        return self._queue.pop(0)


def _usage() -> LLMUsage:
    return LLMUsage(input_tokens=50, output_tokens=20, cost_usd=0.0)


def _router() -> ScriptedRouter:
    # 1) ask for ticket_search  2) end turn  3) synthesis JSON
    return ScriptedRouter([
        LLMCompletion(
            content=[
                LLMToolUseBlock(
                    id="toolu_1",
                    name="ticket_search",
                    input={"query": "charged twice double charge", "limit": 5},
                )
            ],
            stop_reason="tool_use",
            usage=_usage(),
            model="scripted",
        ),
        LLMCompletion(
            content=[LLMTextBlock(text="I have what I need.")],
            stop_reason="end_turn",
            usage=_usage(),
            model="scripted",
        ),
        LLMCompletion(
            content=[LLMTextBlock(text=_SYNTH_JSON)],
            stop_reason="end_turn",
            usage=_usage(),
            model="scripted",
        ),
    ])


async def main() -> None:
    configure_logging()
    # Flush the queue so process_one pops OUR fresh run, not leftover junk.
    await get_redis().delete(queue_key(_VERTICAL))
    run_id = f"debug_{int(time.time())}"
    await enqueue_run(
        run_id,
        tenant_id="local-dev",
        vertical=_VERTICAL,
        query="What billing problems are customers reporting?",
    )
    print(f"enqueued {run_id} — stepping through process_one ...")
    await process_one(_VERTICAL, _router())
    print(f"done: {run_id}")


if __name__ == "__main__":
    asyncio.run(main())
