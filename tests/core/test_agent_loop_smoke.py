"""End-to-end smoke test: scripted LLM → agent loop → ResearchOutput.

The router stub returns a tool_use block on the first call (asking the agent
to fetch MDL-880 via NAIC_lookup), then end_turn, then the synthesis JSON.
We assert the loop:
  - actually invoked the tool
  - produced a ResearchOutput with the right shape
  - cited the model law in findings/sources
  - reported tool_call_count == 1
"""

from __future__ import annotations

from typing import Any

from agentforge.core.llm.types import (
    LLMCompletion,
    LLMTextBlock,
    LLMToolUseBlock,
    LLMUsage,
)
from agentforge.core.runtime.events import AgentEvent
from agentforge.core.runtime.loop import AgentRunArgs, run_agent
from agentforge.verticals.insurance import INSURANCE_VERTICAL


class _ScriptedRouter:
    """Returns a fixed sequence of completions across successive .complete() calls."""

    def __init__(self, completions: list[LLMCompletion]) -> None:
        self._queue = completions
        self.calls = 0

    def supports_multimodal(self) -> bool:
        return True

    async def complete(self, **kwargs: Any) -> LLMCompletion:
        self.calls += 1
        if not self._queue:
            raise AssertionError("scripted router exhausted")
        return self._queue.pop(0)


class _CapturingEmitter:
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []

    def emit(self, event: AgentEvent) -> None:
        self.events.append(event)


def _usage(input_tok: int = 100, output_tok: int = 50, cost: float = 0.001) -> LLMUsage:
    return LLMUsage(input_tokens=input_tok, output_tokens=output_tok, cost_usd=cost)


SYNTHESIS_JSON = """{
  "summary": "MDL-880 governs anti-concurrent causation clauses in property insurance.",
  "findings": [
    {
      "claim": "MDL-880 sets the NAIC model standard for anti-concurrent causation disclosure.",
      "evidence": "NAIC_lookup returned MDL-880 with title 'Anti-Concurrent Causation Disclosure Model Act'.",
      "sourceRef": "MDL-880",
      "confidence": "high"
    }
  ],
  "sources": [
    {
      "id": "MDL-880",
      "title": "Anti-Concurrent Causation Disclosure Model Act",
      "url": "https://content.naic.org/sites/default/files/MO880.pdf",
      "retrievedAt": "2026-05-08T00:00:00Z",
      "dataVintage": "curated index"
    }
  ],
  "flags": [],
  "confidence": "high"
}"""


async def test_loop_invokes_tool_and_synthesizes_output(fake_redis):
    router = _ScriptedRouter([
        # Step 1: model asks to call NAIC_lookup with model_regulation
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
            model="claude-opus-4-7",
        ),
        # Step 2: model decides it has enough; ends turn.
        LLMCompletion(
            content=[LLMTextBlock(text="I have what I need.")],
            stop_reason="end_turn",
            usage=_usage(),
            model="claude-opus-4-7",
        ),
        # Step 3: synthesis — model produces strict JSON.
        LLMCompletion(
            content=[LLMTextBlock(text=SYNTHESIS_JSON)],
            stop_reason="end_turn",
            usage=_usage(input_tok=200, output_tok=120, cost=0.005),
            model="claude-opus-4-7",
        ),
    ])

    emitter = _CapturingEmitter()
    output = await run_agent(
        AgentRunArgs(
            query="What is the NAIC model for anti-concurrent causation?",
            vertical=INSURANCE_VERTICAL,
            router=router,
            emitter=emitter,
        )
    )

    assert output.summary.startswith("MDL-880")
    assert output.confidence == "high"
    assert output.tool_call_count == 1
    assert output.cost_usd > 0
    assert len(output.findings) == 1
    assert output.findings[0].source_ref == "MDL-880"
    assert output.sources[0].id == "MDL-880"

    # Event stream sanity: at minimum run_start, tool_start, tool_result,
    # synthesis_start, output, stop.
    types = [e.type for e in emitter.events]
    assert "run_start" in types
    assert "tool_start" in types
    assert "tool_result" in types
    assert "synthesis_start" in types
    assert "output" in types
    assert "stop" in types
    assert router.calls == 3


async def test_loop_handles_unknown_tool_call_gracefully(fake_redis):
    """If the LLM tries to call a tool we don't have, the loop returns an
    is_error tool_result and continues — never crashes."""
    router = _ScriptedRouter([
        LLMCompletion(
            content=[
                LLMToolUseBlock(id="t1", name="bogus_tool", input={"x": 1})
            ],
            stop_reason="tool_use",
            usage=_usage(),
            model="claude-opus-4-7",
        ),
        LLMCompletion(
            content=[LLMTextBlock(text="ok")],
            stop_reason="end_turn",
            usage=_usage(),
            model="claude-opus-4-7",
        ),
        LLMCompletion(
            content=[LLMTextBlock(text=SYNTHESIS_JSON)],
            stop_reason="end_turn",
            usage=_usage(),
            model="claude-opus-4-7",
        ),
    ])

    output = await run_agent(
        AgentRunArgs(
            query="test",
            vertical=INSURANCE_VERTICAL,
            router=router,
        )
    )
    assert output.summary  # synthesis still runs
    assert output.tool_call_count == 0  # the unknown call wasn't counted as a real tool


async def test_imports_are_clean():
    """Trivial import test — guards against accidental circular imports."""
    from agentforge import core, verticals  # noqa: F401
    from agentforge.core import llm, runtime, schema, tools  # noqa: F401
    from agentforge.verticals.insurance import INSURANCE_VERTICAL as v

    assert v.vertical == "insurance"
    assert {t.name for t in v.tools} == {
        "web_search",
        "state_DOI_query",
        "NAIC_lookup",
        "policy_doc_parse",
        "ISO_forms_search",
    }
