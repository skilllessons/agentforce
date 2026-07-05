"""Custom HTTP agent loop — no LangChain, no LangGraph.

Spec lives in CLAUDE.md. This module implements:
  1. Receive query + vertical config
  2. LOOP up to max_steps:
     - Call LLM with tools
     - If end_turn → synthesize
     - If tool_use → execute tools in parallel, append results
     - Check hard stops on each iteration
  3. Final synthesis pass produces ResearchOutputBody JSON
  4. Wrap with platform-attributed fields → ResearchOutput
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

from nanoid import generate as nanoid

from agentforge.core.llm.types import (
    LLMMessage,
    LLMRouter,
    LLMToolDef,
    LLMToolResultBlock,
    LLMToolUseBlock,
)
from agentforge.core.runtime.events import (
    AgentEventEmitter,
    run_start,
    synthesis_start,
)
from agentforge.core.runtime.events import (
    output as ev_output,
)
from agentforge.core.runtime.events import (
    stop as ev_stop,
)
from agentforge.core.runtime.events import (
    tool_result as ev_tool_result,
)
from agentforge.core.runtime.events import (
    tool_start as ev_tool_start,
)
from agentforge.core.runtime.limits import DEFAULT_LIMITS, RunLimits
from agentforge.core.runtime.stop import StopReason, check_limits
from agentforge.core.runtime.synthesize import synthesize
from agentforge.core.schema import ResearchOutput
from agentforge.core.tools.cache import with_cache
from agentforge.core.tools.protocol import ResearchTool, ToolResult


@dataclass
class VerticalConfig:
    vertical: str
    system_prompt: str
    tools: list[ResearchTool]
    limits: RunLimits = field(default_factory=lambda: DEFAULT_LIMITS)
    model: str | None = None


@dataclass
class AgentRunArgs:
    query: str
    vertical: VerticalConfig
    router: LLMRouter
    run_id: str | None = None
    tenant_id: str = "public"
    context: dict[str, Any] | None = None
    emitter: AgentEventEmitter | None = None


async def run_agent(args: AgentRunArgs) -> ResearchOutput:
    run_id = args.run_id or nanoid(size=12)
    started_at = time.monotonic()
    limits = args.vertical.limits

    def emit(event: Any) -> None:
        if args.emitter is not None:
            args.emitter.emit(event)

    emit(run_start(run_id, args.vertical.vertical))

    tool_map: dict[str, ResearchTool] = {t.name: t for t in args.vertical.tools}
    tool_defs: list[LLMToolDef] = [
        LLMToolDef(name=t.name, description=t.description, input_schema=t.input_schema)
        for t in args.vertical.tools
    ]

    initial_text = (
        f"{args.query}\n\nAdditional context: {json.dumps(args.context)}"
        if args.context
        else args.query
    )
    messages: list[LLMMessage] = [LLMMessage(role="user", content=initial_text)]

    step = 0
    cost_usd = 0.0
    tool_call_count = 0
    stop_reason: StopReason = "end_turn"

    while True:
        limit_hit = check_limits(
            step=step, cost_usd=cost_usd, started_at=started_at, limits=limits
        )
        if limit_hit:
            stop_reason = limit_hit
            break

        completion = await args.router.complete(
            system=args.vertical.system_prompt,
            messages=messages,
            tools=tool_defs,
            model=args.vertical.model,
        )
        cost_usd += completion.usage.cost_usd

        messages.append(LLMMessage(role="assistant", content=completion.content))

        if completion.stop_reason == "end_turn":
            stop_reason = "end_turn"
            break

        tool_uses = [b for b in completion.content if isinstance(b, LLMToolUseBlock)]
        if not tool_uses:
            stop_reason = "end_turn"
            break

        async def run_one(use: LLMToolUseBlock) -> LLMToolResultBlock:
            tool = tool_map.get(use.name)
            if tool is None:
                return LLMToolResultBlock(
                    tool_use_id=use.id,
                    content=json.dumps({"error": f"Unknown tool: {use.name}"}),
                    is_error=True,
                )
            emit(ev_tool_start(use.name, use.input))

            async def invoke() -> ToolResult:
                return await tool.call(use.input)

            result = await with_cache(tool, use.input, invoke, tenant_id=args.tenant_id)
            success = result.success
            emit(ev_tool_result(use.name, success, result.from_cache))

            if result.error:
                payload = json.dumps({"error": result.error})
            else:
                payload = _truncate(json.dumps(result.data, default=str), limits.max_tool_output_chars)

            return LLMToolResultBlock(
                tool_use_id=use.id,
                content=payload,
                is_error=not success,
            )

        results = await asyncio.gather(*(run_one(u) for u in tool_uses))

        # Only real, registered tools count for cost + telemetry. Unknown-tool
        # errors are surfaced to the LLM but don't bill the tenant.
        invoked_tools = [tool_map[u.name] for u in tool_uses if u.name in tool_map]
        tool_call_count += len(invoked_tools)
        cost_usd += sum(t.estimated_cost_usd for t in invoked_tools)

        messages.append(LLMMessage(role="user", content=list(results)))
        step += 1

    emit(synthesis_start())

    body, synth_cost = await synthesize(
        router=args.router,
        system=args.vertical.system_prompt,
        messages=messages,
        model=args.vertical.model,
    )
    cost_usd += synth_cost

    out = ResearchOutput(
        **body.model_dump(by_alias=True),
        runId=run_id,
        elapsedSeconds=round(time.monotonic() - started_at, 3),
        toolCallCount=tool_call_count,
        costUsd=round(cost_usd, 6),
    )

    emit(ev_output(out))
    emit(ev_stop(stop_reason))
    return out


def _truncate(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + f"\n... [truncated {len(s) - max_chars} chars]"


__all__ = ["AgentRunArgs", "VerticalConfig", "run_agent"]
