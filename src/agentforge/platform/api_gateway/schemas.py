from typing import Literal, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentforge.core.runtime.limits import DEFAULT_LIMITS


class RunRequest(BaseModel):
    query: str = Field(min_length=1)
    max_seconds: int | None = None
    max_cost_usd: float| None = None
    webhook_url: str|None= None
    context: dict[str, Any] | None = None
    thread_id: str | None = None
    images: list[dict[str, str]] | None = None  # [{media_type, data(base64)}]
    model_config = ConfigDict(extra="forbid")

    @field_validator("max_cost_usd")
    @classmethod
    def _clamp_cost(cls, v: float | None) -> float | None:
        if v is None:
            return None
        return min(v, DEFAULT_LIMITS.max_cost_usd)    # min(v, 0.50)

    @field_validator("max_seconds")
    @classmethod
    def _clamp_seconds(cls, v: int | None) -> int | None:
        if v is None:
            return None
        return min(v, DEFAULT_LIMITS.max_seconds)


class RunAccepted(BaseModel):
    run_id: str
    status: str = "queued"
    stream_url: str
    estimated_seconds: int

class RunStatus(BaseModel):
    run_id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    elapsed_seconds: float | None = None
    tool_calls: int = 0  # ← wire name is tool_calls, NOT tool_call_count
    cost_usd: float = 0
    result: dict[str, Any] | None = None





