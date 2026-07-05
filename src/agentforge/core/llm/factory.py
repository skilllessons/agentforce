"""Pick a default LLM router based on environment."""

from __future__ import annotations

import os

from agentforge.core.llm.anthropic_router import AnthropicRouter
from agentforge.core.llm.litellm_router import LiteLLMRouter
from agentforge.core.llm.types import LLMRouter


def create_default_router() -> LLMRouter:
    if os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicRouter()
    if os.getenv("LITELLM_API_BASE") or os.getenv("OPENAI_API_KEY"):
        return LiteLLMRouter()
    raise RuntimeError(
        "No LLM credentials configured (ANTHROPIC_API_KEY or LITELLM_API_BASE)"
    )
