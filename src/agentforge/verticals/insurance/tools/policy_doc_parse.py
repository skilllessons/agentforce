"""policy_doc_parse — extract text from a policy PDF (URL or file ref).

The structured-field extraction (declarations, exclusions, limits) is a Phase 1
follow-up. For now we return the raw text excerpt, page count, and file hash;
the agent can reason over the excerpt directly.
"""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from typing import Any

import httpx
import pdfplumber
from pydantic import BaseModel, Field, model_validator

from agentforge.core.tools.protocol import ToolResult
from agentforge.core.tools.validate import validate_input


class _FileRef(BaseModel):
    file_id: str = Field(alias="fileId")


class _Input(BaseModel):
    file_url: str | None = Field(default=None, alias="fileUrl")
    file_ref: _FileRef | None = Field(default=None, alias="fileRef")

    @model_validator(mode="after")
    def _exactly_one(self) -> _Input:
        if (self.file_url is None) == (self.file_ref is None):
            raise ValueError("Exactly one of fileUrl or fileRef is required")
        return self


_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "fileUrl": {"type": "string", "format": "uri"},
        "fileRef": {
            "type": "object",
            "properties": {"fileId": {"type": "string"}},
            "required": ["fileId"],
        },
    },
    "additionalProperties": False,
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "fileHash": {"type": "string"},
        "pageCount": {"type": "integer"},
        "rawTextExcerpt": {"type": "string"},
    },
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


async def _load_bytes(input_: _Input) -> tuple[bytes, str]:
    if input_.file_ref is not None:
        # Lazy-import to avoid a hard dependency when only file_url is used.
        from agentforge.core.file_storage import (
            create_file_storage,  # type: ignore[import-not-found]
        )

        storage = create_file_storage()
        obj = await storage.get(input_.file_ref.file_id)
        return obj.bytes, f"agentforge://file/{input_.file_ref.file_id}"

    assert input_.file_url is not None
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        resp = await client.get(input_.file_url, follow_redirects=True)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch PDF: {resp.status_code}")
    return resp.content, input_.file_url


async def _call(input_: dict[str, Any]) -> ToolResult:
    try:
        validated = validate_input(input_, _Input)
    except Exception as e:
        return ToolResult(data=None, error=str(e), retrievedAt=_now_iso())

    retrieved_at = _now_iso()

    try:
        data, source_url = await _load_bytes(validated)
    except httpx.TimeoutException:
        return ToolResult(data=None, error="PDF fetch timed out after 15s", retrievedAt=retrieved_at)
    except Exception as e:
        return ToolResult(data=None, error=str(e), retrievedAt=retrieved_at)

    file_hash = hashlib.sha256(data).hexdigest()[:16]

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            page_count = len(pdf.pages)
            text_parts = []
            for page in pdf.pages[:20]:  # cap pages for safety
                t = page.extract_text() or ""
                text_parts.append(t)
            full_text = "\n".join(text_parts)
    except Exception as e:
        return ToolResult(data=None, error=f"PDF parse failed: {e}", retrievedAt=retrieved_at)

    return ToolResult(
        data={
            "fileHash": file_hash,
            "pageCount": page_count,
            "rawTextExcerpt": full_text[:4000],
        },
        sourceUrl=source_url,
        retrievedAt=retrieved_at,
    )


class _PolicyDocParseTool:
    name = "policy_doc_parse"
    description = (
        "Extracts text and structured fields from a policy PDF (declarations page, "
        "endorsements, exclusions, limits). Accepts either fileUrl (public URL) or "
        "fileRef.fileId (file uploaded via /v1/files). Use ONLY when the user references "
        "a specific policy document."
    )
    input_schema = _INPUT_SCHEMA
    output_schema = _OUTPUT_SCHEMA
    cache_ttl_seconds = 0  # callers cache by file hash
    estimated_cost_usd = 0.005
    vertical = "insurance"

    async def call(self, input_: dict[str, Any]) -> ToolResult:
        return await _call(input_)


policy_doc_parse_tool = _PolicyDocParseTool()
