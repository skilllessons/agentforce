"""ResearchTool protocol — every domain connector implements this exact shape."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

JSONSchema = dict[str, Any]


class ToolResult(BaseModel):
    """Outcome of one tool invocation. Tools NEVER raise — they return this."""

    model_config = ConfigDict(extra="allow")

    data: Any | None
    error: str | None = None
    source_url: str | None = Field(default=None, alias="sourceUrl")
    retrieved_at: str = Field(alias="retrievedAt")
    raw_response: Any | None = Field(default=None, alias="rawResponse")
    from_cache: bool = Field(default=False, alias="fromCache")

    @property
    def success(self) -> bool:
        return self.data is not None and not self.error


@runtime_checkable
class ResearchTool(Protocol):
    """The contract every tool implements.

    Implementations are typically module-level singletons constructed via the
    :func:`agentforge.core.tools.factory.tool` decorator or by creating a
    dataclass-like instance. The agent runtime introspects ``input_schema`` for
    the LLM tool spec.
    """

    name: str
    description: str
    input_schema: JSONSchema
    output_schema: JSONSchema
    cache_ttl_seconds: int
    estimated_cost_usd: float
    vertical: str | None

    async def call(self, input_: dict[str, Any]) -> ToolResult: ...
