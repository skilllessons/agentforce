"""ResearchOutput and friends — the canonical agent response shape.

Every vertical, every query produces this shape. Pydantic models double as
JSON-schema sources for tool definitions and as runtime validators on the
synthesis output.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

Confidence = Literal["high", "medium", "low"]


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    evidence: str
    source_ref: str = Field(alias="sourceRef")
    confidence: Confidence


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    title: str
    url: HttpUrl | None = None
    retrieved_at: str = Field(alias="retrievedAt")
    data_vintage: str | None = Field(default=None, alias="dataVintage")


class ResearchOutputBody(BaseModel):
    """The LLM-produced portion of a research output.

    Excludes platform-attributed fields (run_id, elapsed, cost) so the model
    isn't asked to invent them. The runtime fills those in.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    summary: str
    findings: list[Finding]
    sources: list[Source]
    flags: list[str]
    confidence: Confidence


class ResearchOutput(ResearchOutputBody):
    run_id: str = Field(alias="runId")
    elapsed_seconds: float = Field(alias="elapsedSeconds")
    tool_call_count: int = Field(alias="toolCallCount", ge=0)
    cost_usd: float = Field(alias="costUsd", ge=0)
