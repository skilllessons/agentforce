"""Worker loop — pull a run id, execute the agent, persist the result.

This is the glue between the queue and the core agent runtime. It owns the
run's lifecycle transitions (mark_running -> mark_completed / mark_failed)
and mirrors key moments into run_events.

For Sunday's milestone the LLM is SCRIPTED (reuse the test fixture router) —
do NOT wire real Anthropic here yet. The `router` is passed in so the CLI /
tests can inject either a scripted or a live router.
"""

from __future__ import annotations

import json

from agentforge.core.llm.types import LLMRouter
from agentforge.core.runtime.loop import AgentRunArgs, VerticalConfig, run_agent
from agentforge.core.db.repos import run_events, runs
from agentforge.platform.run_orchestrator.queue import dequeue_run
from agentforge.core.observability import bind_run, clear_run, get_logger

log = get_logger("worker.loop")


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
        await run_events.append(run_id, tenant_id=row["tenant_id"], kind="run_start")
        log.info("run.start", query=row["query"][:80])

        cfg = _load_vertical(vertical)
        ctx = row["context"]
        if isinstance(ctx, str):
            ctx = json.loads(ctx)

        images = row["attachments"]  # JSONB → str; base64 image inputs
        if isinstance(images, str):
            images = json.loads(images)

        args = AgentRunArgs(
            query=row["query"],
            vertical=cfg,
            router=router,
            run_id=run_id,
            tenant_id=row["tenant_id"],
            context=ctx or None,
            images=images or None,
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
            await run_events.append(
                run_id, tenant_id=row["tenant_id"], kind="output",
                payload=out.model_dump(by_alias=True, mode="json"),
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
        clear_run()

    return run_id


async def run_forever(vertical: str, router: LLMRouter) -> None:
    """Process runs forever. dequeue_run blocks, so this won't busy-spin."""
    while True:
        await process_one(vertical, router)
