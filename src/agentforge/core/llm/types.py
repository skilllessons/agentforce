"""Shared LLM message + content-block types.

Modeled on Anthropic's content-block shape (the most expressive of the major
providers). LiteLLM completions are adapted into this shape so the agent loop
stays provider-agnostic.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

LLMImageMediaType = Literal["image/jpeg", "image/png", "image/gif", "image/webp"]


class LLMTextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class _ImageBase64Source(BaseModel):
    type: Literal["base64"] = "base64"
    media_type: LLMImageMediaType
    data: str


class _ImageUrlSource(BaseModel):
    type: Literal["url"] = "url"
    url: str


class LLMImageBlock(BaseModel):
    type: Literal["image"] = "image"
    source: _ImageBase64Source | _ImageUrlSource


class _DocBase64Source(BaseModel):
    type: Literal["base64"] = "base64"
    media_type: Literal["application/pdf"] = "application/pdf"
    data: str


class _DocUrlSource(BaseModel):
    type: Literal["url"] = "url"
    url: str


class LLMDocumentBlock(BaseModel):
    type: Literal["document"] = "document"
    source: _DocBase64Source | _DocUrlSource
    title: str | None = None


class LLMToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class LLMToolResultBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


LLMContentBlock = (
    LLMTextBlock
    | LLMImageBlock
    | LLMDocumentBlock
    | LLMToolUseBlock
    | LLMToolResultBlock
)


class LLMMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str | list[LLMContentBlock]


class LLMToolDef(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class LLMUsage(BaseModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


class LLMCompletion(BaseModel):
    content: list[LLMContentBlock]
    stop_reason: str
    usage: LLMUsage
    model: str


@runtime_checkable
class LLMRouter(Protocol):
    """Provider-agnostic LLM contract."""

    def supports_multimodal(self) -> bool: ...

    async def complete(
        self,
        *,
        system: str,
        messages: list[LLMMessage],
        tools: list[LLMToolDef] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model: str | None = None,
    ) -> LLMCompletion: ...
