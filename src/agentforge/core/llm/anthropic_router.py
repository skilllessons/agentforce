"""Anthropic-native router with prompt caching on the system prompt."""

from __future__ import annotations

import os
from typing import Any

from anthropic import AsyncAnthropic

from agentforge.core.llm.pricing import estimate_cost_usd
from agentforge.core.llm.types import (
    LLMCompletion,
    LLMContentBlock,
    LLMMessage,
    LLMTextBlock,
    LLMToolDef,
    LLMToolUseBlock,
    LLMUsage,
)


class AnthropicRouter:
    def __init__(self, *, api_key: str | None = None, default_model: str | None = None) -> None:
        self._client = AsyncAnthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self._default_model = (
            default_model
            or os.getenv("ANTHROPIC_DEFAULT_MODEL")
            or "claude-opus-4-7"
        )

    def supports_multimodal(self) -> bool:
        return True

    async def complete(
        self,
        *,
        system: str,
        messages: list[LLMMessage],
        tools: list[LLMToolDef] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model: str | None = None,
    ) -> LLMCompletion:
        chosen_model = model or self._default_model

        response = await self._client.messages.create(
            model=chosen_model,
            max_tokens=max_tokens,
            system=[
                {"type": "text",
                 "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in (tools or [])
            ],
            messages=[_serialize_message(m) for m in messages],
        )

        content: list[LLMContentBlock] = []
        for block in response.content:
            if block.type == "text":
                content.append(LLMTextBlock(text=block.text))
            elif block.type == "tool_use":
                content.append(
                    LLMToolUseBlock(id=block.id, name=block.name, input=dict(block.input))
                )
            else:
                # Future block types fall back to a text representation so the
                # loop never crashes on an unknown shape.
                content.append(LLMTextBlock(text=str(block)))

        return LLMCompletion(
            content=content,
            stop_reason=response.stop_reason or "end_turn",
            usage=LLMUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cost_usd=estimate_cost_usd(
                    chosen_model,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                ),
            ),
            model=chosen_model,
        )


def _serialize_message(m: LLMMessage) -> dict[str, Any]:
    if isinstance(m.content, str):
        return {"role": m.role, "content": m.content}
    return {
        "role": m.role,
        "content": [b.model_dump(exclude_none=True) for b in m.content],
    }
