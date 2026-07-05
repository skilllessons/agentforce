"""AgentEvent shapes emitted during a run (pubsub + DB persistence)."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel

from agentforge.core.schema import ResearchOutput


class _RunStart(BaseModel):
    type: Literal["run_start"] = "run_start"
    runId: str
    vertical: str
    attachmentCount: int = 0


class _ToolStart(BaseModel):
    type: Literal["tool_start"] = "tool_start"
    tool: str
    input: Any


class _ToolResult(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool: str
    success: bool
    cached: bool


class _AttachmentResolved(BaseModel):
    type: Literal["attachment_resolved"] = "attachment_resolved"
    fileId: str
    kind: str
    bytes: int


class _AttachmentSkipped(BaseModel):
    type: Literal["attachment_skipped"] = "attachment_skipped"
    fileId: str
    reason: str


class _SynthesisStart(BaseModel):
    type: Literal["synthesis_start"] = "synthesis_start"


class _Output(BaseModel):
    type: Literal["output"] = "output"
    output: ResearchOutput


class _Stop(BaseModel):
    type: Literal["stop"] = "stop"
    reason: str


class _Error(BaseModel):
    type: Literal["error"] = "error"
    message: str


AgentEvent = (
    _RunStart
    | _ToolStart
    | _ToolResult
    | _AttachmentResolved
    | _AttachmentSkipped
    | _SynthesisStart
    | _Output
    | _Stop
    | _Error
)


class AgentEventEmitter(Protocol):
    def emit(self, event: AgentEvent) -> None: ...


# Convenience constructors so tools can build typed events without importing
# the underscore-prefixed classes.
def run_start(run_id: str, vertical: str, attachment_count: int = 0) -> AgentEvent:
    return _RunStart(runId=run_id, vertical=vertical, attachmentCount=attachment_count)


def tool_start(tool: str, input_: Any) -> AgentEvent:
    return _ToolStart(tool=tool, input=input_)


def tool_result(tool: str, success: bool, cached: bool) -> AgentEvent:
    return _ToolResult(tool=tool, success=success, cached=cached)


def synthesis_start() -> AgentEvent:
    return _SynthesisStart()


def output(o: ResearchOutput) -> AgentEvent:
    return _Output(output=o)


def stop(reason: str) -> AgentEvent:
    return _Stop(reason=reason)


def error(message: str) -> AgentEvent:
    return _Error(message=message)
