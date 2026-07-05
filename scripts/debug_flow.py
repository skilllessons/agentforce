"""Debug entry — step through the full run flow with a SCRIPTED LLM.

Free, deterministic, restartable: the router returns canned completions, so no
Anthropic key, no cost, no network latency stalling the debugger. The rest of
the path is the REAL code — enqueue -> claim -> agent loop -> NAIC tool
(offline curated index) -> synthesis -> persist.

Postgres + Redis must be up:  bash scripts/bootstrap-local.sh

In PyCharm: Run config = Script path -> this file, interpreter = project .venv,
working dir = repo root. Drop breakpoints (see the README block below) and Debug.

Good breakpoints to watch the flow:
  platform/worker/loop.py                  -> process_one  (dequeue, claim, persist)
  core/runtime/loop.py                     -> run_agent    (the LLM<->tool loop)
  verticals/insurance/tools/naic_lookup.py -> _lookup_model_regulation
  core/runtime/synthesize.py               -> synthesize / _extract_json
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

_SYNTH_JSON = """{
  "summary": "MDL-880 governs anti-concurrent causation disclosure in property insurance.",
  "findings": [
    {
      "claim": "MDL-880 is the NAIC model standard for ACC disclosure.",
      "evidence": "NAIC_lookup returned MDL-880 from the curated model-law index.",
      "sourceRef": "MDL-880",
      "confidence": "high"
    }
  ],
  "sources": [
    {
      "id": "MDL-880",
      "title": "Anti-Concurrent Causation Disclosure Model Act",
      "url": "https://content.naic.org/sites/default/files/MO880.pdf",
      "retrievedAt": "2026-01-30T00:00:00Z",
      "dataVintage": "curated index"
    }
  ],
  "flags": [],
  "confidence": "high"
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
    # 1) ask for NAIC_lookup  2) end turn  3) synthesis JSON
    return ScriptedRouter([
        LLMCompletion(
            content=[
                LLMToolUseBlock(
                    id="toolu_1",
                    name="NAIC_lookup",
                    input={"query": "anti-concurrent causation", "type": "model_regulation"},
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
    await get_redis().delete(queue_key("insurance"))
    run_id = f"debug_{int(time.time())}"
    await enqueue_run(
        run_id,
        tenant_id="local-dev",
        vertical="insurance",
        query="What does NAIC MDL-880 say about anti-concurrent causation?",
    )
    print(f"enqueued {run_id} — stepping through process_one ...")
    await process_one("insurance", _router())
    print(f"done: {run_id}")


if __name__ == "__main__":
    asyncio.run(main())
