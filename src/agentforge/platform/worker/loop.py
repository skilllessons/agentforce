"""Worker loop — pull a run id, execute the agent, persist the result.

Glue between the queue and the core agent runtime. Owns the run's lifecycle
transitions (mark_running -> mark_completed / mark_failed) and persists the
agent's event stream (run_start, tool_start, tool_result, synthesis_start,
output) into run_events so the studio can render a live trace. The `router`
is injected (real Anthropic via create_default_router, or a test stub).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from agentforge.core.llm.types import LLMRouter
from agentforge.core.runtime.loop import AgentRunArgs, VerticalConfig, run_agent
from agentforge.core.db.repos import run_events, runs
from agentforge.platform.run_orchestrator.queue import dequeue_run
from agentforge.core.observability import bind_run, clear_run, get_logger

log = get_logger("worker.loop")


class _DBEmitter:
    """Persists each agent event to run_events (for the studio's live trace).

    emit() is sync (called from the loop) — it just puts the event on an
    asyncio.Queue. A background drainer (started in process_one) awaits the
    queue and writes to Postgres in order, so persistence is reliable and
    ordered, not fire-and-forget. A monotonic _seq is stamped for the UI.
    """

    def __init__(self, run_id: str, tenant_id: str) -> None:
        self.run_id = run_id
        self.tenant_id = tenant_id
        self.queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()
        self._seq = 0

    def emit(self, event: Any) -> None:
        payload = event.model_dump(by_alias=True, mode="json")
        payload["_seq"] = self._seq
        self._seq += 1
        self.queue.put_nowait((event.type, payload))


async def _drain_events(emitter: _DBEmitter) -> None:
    """Background task: persist queued events in order until the sentinel."""
    while True:
        item = await emitter.queue.get()
        if item is None:  # sentinel → run finished
            return
        kind, payload = item
        try:
            await run_events.append(
                emitter.run_id, tenant_id=emitter.tenant_id, kind=kind, payload=payload
            )
        except Exception as e:  # a trace-write failure must not kill the run
            log.warning("event.persist_failed", error=str(e))


def _load_vertical(vertical: str) -> VerticalConfig:
    """Build the VerticalConfig (system prompt + tools) for a vertical name."""
    if vertical == "insurance":
        from agentforge.verticals.insurance import INSURANCE_VERTICAL
        return INSURANCE_VERTICAL
    raise ValueError(f"unknown vertical: {vertical}")


async def process_one(vertical: str, router: LLMRouter) -> str | None:
    """Dequeue one run, execute it, persist. Returns run_id, or None if idle."""
    run_id = await dequeue_run(vertical)
    if run_id is None:
        return None

    row = await runs.get(run_id)
    bind_run(run_id=run_id, tenant_id=row["tenant_id"], vertical=vertical)
    try:
        claimed = await runs.mark_running(run_id)
        if not claimed:
            log.info("run.skipped", reason="not_queued")
            return run_id
        log.info("run.start", query=row["query"][:80])

        cfg = _load_vertical(vertical)
        ctx = row["context"]
        if isinstance(ctx, str):
            ctx = json.loads(ctx)

        images = row["attachments"]  # JSONB → str; base64 image inputs
        if isinstance(images, str):
            images = json.loads(images)

        # Emitter persists run_start/tool_start/tool_result/synthesis_start/output
        # to run_events as they fire → the studio polls them for a live trace.
        emitter = _DBEmitter(run_id, row["tenant_id"])
        drainer = asyncio.create_task(_drain_events(emitter))
        args = AgentRunArgs(
            query=row["query"],
            vertical=cfg,
            router=router,
            run_id=run_id,
            tenant_id=row["tenant_id"],
            context=ctx or None,
            images=images or None,
            emitter=emitter,
        )

        try:
            out = await run_agent(args)
            await runs.mark_completed(
                run_id,
                result=out.model_dump(by_alias=True, mode="json"),
                cost_usd=out.cost_usd,
                tool_call_count=out.tool_call_count,
                elapsed_seconds=out.elapsed_seconds,
            )
            log.info(
                "run.completed",
                cost_usd=out.cost_usd,
                tools=out.tool_call_count,
                elapsed=out.elapsed_seconds,
            )
        except Exception as e:
            await runs.mark_failed(run_id, str(e))
            await run_events.append(
                run_id, tenant_id=row["tenant_id"], kind="error",
                payload={"error": str(e)},
            )
            log.warning("run.failed", error=str(e))
        finally:
            emitter.queue.put_nowait(None)  # sentinel → flush the drainer
            await drainer
    finally:
        clear_run()

    return run_id


async def run_forever(vertical: str, router: LLMRouter) -> None:
    """Process runs forever. dequeue_run blocks, so this won't busy-spin."""
    while True:
        await process_one(vertical, router)
