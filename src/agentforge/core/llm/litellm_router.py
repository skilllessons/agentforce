"""LiteLLM-backed fallback router.

Uses litellm.acompletion which speaks OpenAI's chat-completions shape and
translates to whichever provider is configured. We collapse non-text content
(image/document/tool_result) to text descriptions because not every backend
supports those blocks; callers should check ``supports_multimodal()``.
"""

from __future__ import annotations

import json
import os
from typing import Any

import litellm

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


class LiteLLMRouter:
    def __init__(self, *, api_base: str | None = None, default_model: str | None = None) -> None:
        self._api_base = api_base or os.getenv("LITELLM_API_BASE")
        self._default_model = default_model or "gpt-4o-mini"

    def supports_multimodal(self) -> bool:
        return False

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

        kwargs: dict[str, Any] = {
            "model": chosen_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                *[
                    {
                        "role": m.role,
                        "content": (
                            m.content
                            if isinstance(m.content, str)
                            else _flatten_blocks(m.content)
                        ),
                    }
                    for m in messages
                ],
            ],
        }
        if self._api_base:
            kwargs["api_base"] = self._api_base
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ]

        response = await litellm.acompletion(**kwargs)
        choice = response.choices[0]
        message = choice.message
        usage = response.usage

        content: list[LLMContentBlock] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                content.append(
                    LLMToolUseBlock(
                        id=tc.id,
                        name=tc.function.name,
                        input=json.loads(tc.function.arguments or "{}"),
                    )
                )
        else:
            content.append(LLMTextBlock(text=message.content or ""))

        stop_reason = "tool_use" if choice.finish_reason == "tool_calls" else "end_turn"

        return LLMCompletion(
            content=content,
            stop_reason=stop_reason,
            usage=LLMUsage(
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost_usd=estimate_cost_usd(
                    chosen_model, usage.prompt_tokens, usage.completion_tokens
                ),
            ),
            model=chosen_model,
        )


def _flatten_blocks(blocks: list[LLMContentBlock]) -> str:
    parts: list[str] = []
    for b in blocks:
        match b.type:
            case "text":
                parts.append(b.text)  # type: ignore[union-attr]
            case "image":
                parts.append("[image attachment — provider does not support binary]")
            case "document":
                parts.append("[pdf attachment — provider does not support binary]")
            case "tool_use":
                parts.append(
                    f"[tool_use {b.name}({json.dumps(b.input)})]"  # type: ignore[union-attr]
                )
            case "tool_result":
                parts.append(f"[tool_result {b.tool_use_id}: {b.content}]")  # type: ignore[union-attr]
    return "\n".join(parts)
