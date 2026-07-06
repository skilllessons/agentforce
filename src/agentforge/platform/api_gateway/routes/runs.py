from __future__ import annotations
import json
import asyncio
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, HTTPException
from nanoid import generate as nanoid
from agentforge.core.db.repos import runs, run_events, sessions
from agentforge.platform.run_orchestrator.queue import enqueue_run
from agentforge.platform.api_gateway.schemas import RunRequest, RunAccepted, RunStatus

_TENANT = "local-dev"  # TODO: from auth (T4)


_STREAM_TIMEOUT_S = 120     # stop streaming after this long (run cap is 90s)
_POLL_INTERVAL_S = 0.5      # how often to re-check run_events
router = APIRouter(prefix="/v1", tags=["runs"])

def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    async def gen():
        seen = 0
        for _ in range(int(_STREAM_TIMEOUT_S / _POLL_INTERVAL_S)):
            events = await run_events.list_for_run(run_id)
            for e in events[seen:]:
                yield _sse(e["kind"], e["payload"])
                seen += 1
                if e["kind"] in ("output", "error"):
                    yield _sse("done", "{}")
                    return
            await asyncio.sleep(_POLL_INTERVAL_S)
        yield _sse("done", "{}")
    return StreamingResponse(gen(), media_type="text/event-stream")

@router.post("/agents/{vertical}/run", status_code=202, response_model=RunAccepted)
async def create_run(vertical: str, req: RunRequest) -> RunAccepted:
    run_id = nanoid(size=12)
    limits: dict[str, float | int] = {}
    if req.max_cost_usd is not None:
        limits["max_cost_usd"] = req.max_cost_usd
    if req.max_seconds is not None:
        limits["max_seconds"] = req.max_seconds

    # Multi-turn context: if this run is part of a thread, prepend the compacted
    # prior turns so the agent can answer follow-ups.
    context = dict(req.context or {})
    if req.thread_id:
        history = await runs.history_for_thread(req.thread_id)
        if history:
            context["conversation"] = history
        await sessions.touch(req.thread_id, title=req.query[:80])

    await enqueue_run(
        run_id, tenant_id=_TENANT, vertical=vertical, query=req.query,
        context=context or None, limits=limits, thread_id=req.thread_id,
        attachments=req.images,
    )
    return RunAccepted(run_id=run_id, status="queued", stream_url=f"/v1/runs/{run_id}/stream", estimated_seconds=40)

@router.get("/runs")
async def list_runs() -> dict:
    rows = await runs.list_recent(_TENANT, limit=30)
    return {"runs": rows}

@router.get("/runs/{run_id}/events")
async def list_run_events(run_id: str) -> dict:
    rows = await run_events.list_for_run(run_id)
    for r in rows:  # JSONB payload comes back as a string
        if isinstance(r.get("payload"), str):
            r["payload"] = json.loads(r["payload"])
    return {"events": rows}

@router.post("/agents/{vertical}/sessions", status_code=201)
async def create_session(vertical: str) -> dict:
    session_id = nanoid(size=12)
    await sessions.create(session_id, tenant_id=_TENANT, vertical=vertical)
    return {"thread_id": session_id}

@router.get("/sessions")
async def list_sessions() -> dict:
    rows = await sessions.list_recent(_TENANT, limit=30)
    return {"sessions": rows}

@router.get("/sessions/{thread_id}/runs")
async def list_session_runs(thread_id: str) -> dict:
    rows = await runs.list_for_thread(thread_id)
    for r in rows:
        if isinstance(r.get("result"), str):  # JSONB comes back as a string
            r["result"] = json.loads(r["result"])
        # NUMERIC comes back as Decimal → coerce so the JSON is a number, not a string.
        r["cost_usd"] = float(r["cost_usd"]) if r["cost_usd"] is not None else 0.0
        r["elapsed_seconds"] = (
            float(r["elapsed_seconds"]) if r["elapsed_seconds"] is not None else None
        )
    return {"runs": rows}

@router.get("/runs/{run_id}", response_model=RunStatus)
async def get_run(run_id: str) -> RunStatus:
    row = await runs.get(run_id)

    if row is None:
        raise HTTPException(status_code=404, detail="run not found")

    result = row["result"];
    if isinstance(result, str): result = json.loads(result)

    return RunStatus(
        run_id=run_id,
        status=row["status"],
        elapsed_seconds=row["elapsed_seconds"],
        tool_calls=row["tool_call_count"],
        cost_usd=float(row["cost_usd"]),  # ← DB col → wire name
        result=result,
    )