"""Final synthesis pass — model produces strict JSON conforming to ResearchOutputBody."""

from __future__ import annotations

import json
import re

from agentforge.core.llm.types import LLMMessage, LLMRouter, LLMTextBlock
from agentforge.core.schema import ResearchOutputBody

SYNTHESIS_INSTRUCTIONS = """Synthesize the tool results above into the final answer.

Respond ONLY with valid JSON matching this exact schema. No prose, no markdown, no code fences.
{
  "summary": "string",
  "findings": [{ "claim": "string", "evidence": "string", "sourceRef": "string", "confidence": "high|medium|low" }],
  "sources": [{ "id": "string", "title": "string", "url": "string|null", "retrievedAt": "ISO timestamp", "dataVintage": "string|null" }],
  "flags": ["string"],
  "confidence": "high|medium|low"
}"""


async def synthesize(
    *,
    router: LLMRouter,
    system: str,
    messages: list[LLMMessage],
    model: str | None = None,
) -> tuple[ResearchOutputBody, float]:
    final_messages = [
        *messages,
        LLMMessage(role="user", content=SYNTHESIS_INSTRUCTIONS),
    ]
    completion = await router.complete(
        system=system,
        messages=final_messages,
        max_tokens=4096,
        temperature=0,
        model=model,
    )

    text = "\n".join(
        block.text for block in completion.content if isinstance(block, LLMTextBlock)
    ).strip()

    payload = _extract_json(text)
    body = ResearchOutputBody.model_validate(payload)
    return body, completion.usage.cost_usd


def _extract_json(text: str) -> object:
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    candidate = fenced.group(1) if fenced else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in synthesis output")
    return json.loads(candidate[start : end + 1])
