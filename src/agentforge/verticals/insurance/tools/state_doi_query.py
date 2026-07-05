"""state_DOI_query — placeholder until per-state portals are wired.

State DOIs have no consistent API; each is a separate scrape. Phase 1 priority
states: CA (CDI), TX (TDI), FL (OIR), NY (NYDFS), IL (IDOI). Until those land,
this returns a structured null with a clear notice so the agent loop can
gracefully fall back to web_search.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from agentforge.core.tools.protocol import ToolResult
from agentforge.core.tools.validate import validate_input

_STATES = frozenset({
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT",
    "VT", "VA", "WA", "WV", "WI", "WY",
})


class _Input(BaseModel):
    state: str
    topic: str = Field(min_length=2)
    document_type: Literal["bulletin", "rate_filing", "enforcement", "admitted_status", "all"] = (
        "all"
    )

    @field_validator("state")
    @classmethod
    def _valid_state(cls, v: str) -> str:
        if v.upper() not in _STATES:
            raise ValueError(f"unknown state: {v}")
        return v.upper()


_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "state": {"type": "string", "enum": sorted(_STATES)},
        "topic": {"type": "string"},
        "documentType": {
            "type": "string",
            "enum": ["bulletin", "rate_filing", "enforcement", "admitted_status", "all"],
            "default": "all",
        },
    },
    "required": ["state", "topic"],
    "additionalProperties": False,
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "state": {"type": "string"},
        "documents": {"type": "array"},
        "notice": {"type": "string"},
    },
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _call(input_: dict[str, Any]) -> ToolResult:
    if "documentType" in input_ and "document_type" not in input_:
        input_ = {**input_, "document_type": input_["documentType"]}
    try:
        validated = validate_input(input_, _Input)
    except Exception as e:
        return ToolResult(data=None, error=str(e), retrievedAt=_now_iso())

    return ToolResult(
        data={
            "state": validated.state,
            "documents": [],
            "notice": (
                f"state_DOI_query connector for {validated.state} is not yet wired to "
                "live data; route to web_search for now."
            ),
        },
        sourceUrl=f"https://doi.{validated.state.lower()}.gov",
        retrievedAt=_now_iso(),
    )


class _StateDOITool:
    name = "state_DOI_query"
    description = (
        "Fetches regulatory bulletins, rate filings, admitted/non-admitted carrier status, "
        "and enforcement actions from state Department of Insurance portals. Use for "
        "state-specific regulation, prompt-payment rules, surplus lines requirements, and "
        "filing rules. Specify the state."
    )
    input_schema = _INPUT_SCHEMA
    output_schema = _OUTPUT_SCHEMA
    cache_ttl_seconds = 21_600  # 6h
    estimated_cost_usd = 0.001
    vertical = "insurance"

    async def call(self, input_: dict[str, Any]) -> ToolResult:
        return await _call(input_)


state_doi_query_tool = _StateDOITool()
