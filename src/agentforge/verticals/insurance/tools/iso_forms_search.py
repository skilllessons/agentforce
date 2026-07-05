"""ISO_forms_search — placeholder until a Verisk source is decided.

Phase 1 decision pending: paid Verisk subscription (real moat) vs. Cornell LII
+ scraped public references (free, weaker). Until that lands this returns a
structured null with a clear notice.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from agentforge.core.tools.protocol import ToolResult
from agentforge.core.tools.validate import validate_input

_LOB = Literal["CGL", "BOP", "HO", "Auto", "Property", "Umbrella", "Workers Comp"]


class _Input(BaseModel):
    form_number: str | None = Field(default=None, alias="formNumber")
    keyword: str | None = None
    line_of_business: _LOB | None = Field(default=None, alias="lineOfBusiness")

    @model_validator(mode="after")
    def _at_least_one(self) -> _Input:
        if self.form_number is None and self.keyword is None:
            raise ValueError("formNumber or keyword is required")
        return self


_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "formNumber": {"type": "string"},
        "keyword": {"type": "string"},
        "lineOfBusiness": {
            "type": "string",
            "enum": ["CGL", "BOP", "HO", "Auto", "Property", "Umbrella", "Workers Comp"],
        },
    },
    "additionalProperties": False,
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"forms": {"type": "array"}, "notice": {"type": "string"}},
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _call(input_: dict[str, Any]) -> ToolResult:
    try:
        validated = validate_input(input_, _Input)
    except Exception as e:
        return ToolResult(data=None, error=str(e), retrievedAt=_now_iso())

    return ToolResult(
        data={
            "forms": [],
            "notice": (
                "ISO_forms_search connector is not yet wired to a live source. "
                f"Query: {validated.model_dump(by_alias=True, exclude_none=True)}"
            ),
        },
        sourceUrl="https://www.verisk.com/insurance/products/iso-forms",
        retrievedAt=_now_iso(),
    )


class _ISOFormsSearchTool:
    name = "ISO_forms_search"
    description = (
        "Looks up ISO standard form numbers (e.g. CG 00 01, BP 00 03, HO 00 03) and returns "
        "the canonical form text, revision date, and known endorsement modifications. Use "
        "whenever the query references coverage language, form numbers, or standard exclusions."
    )
    input_schema = _INPUT_SCHEMA
    output_schema = _OUTPUT_SCHEMA
    cache_ttl_seconds = 86_400
    estimated_cost_usd = 0.001
    vertical = "insurance"

    async def call(self, input_: dict[str, Any]) -> ToolResult:
        return await _call(input_)


iso_forms_search_tool = _ISOFormsSearchTool()
