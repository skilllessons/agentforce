"""Retrieval + behavior eval harness for the support vertical.

Runs each golden query through the REAL agent loop (live Claude, real
ticket_search against local Postgres) and scores what the answer CITED against
the ticket ids a human expected.

Run:
    uv run agentforge-eval-support                    # all (non-skipped) queries
    uv run agentforge-eval-support --limit 3          # first 3 (cheap demo)
    uv run agentforge-eval-support --ids billing_overview

Needs ANTHROPIC_API_KEY and Postgres with tickets seeded
(`uv run python scripts/seed_tickets.py`). Runs as tenant `local-dev`.
No queue, no worker: calls run_agent directly. Stop nothing else to run it.

Each run prints a scorecard and writes a JSON report under eval/reports/.
The report is the M2 baseline that M3 (semantic search, model choice) must beat.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from agentforge.core.db.client import close_db
from agentforge.core.llm.factory import create_default_router
from agentforge.core.llm.types import LLMRouter
from agentforge.core.runtime.loop import AgentRunArgs, run_agent
from agentforge.core.schema import ResearchOutput
from agentforge.verticals.support import SUPPORT_VERTICAL

_DIR = Path(__file__).parent
_QUERIES_PATH = _DIR / "golden_queries.json"
_REPORTS_DIR = _DIR / "reports"
_TENANT = "local-dev"

# Every acme-test ticket id. Seeing one in a local-dev answer is a tenant leak.
_OTHER_TENANT_IDS = {"9001", "9002", "9003", "9004"}


class _Capture:
    """Minimal emitter that records the run's event stream."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    def emit(self, event: Any) -> None:
        self.events.append(event)


def _tools_called(cap: _Capture) -> list[str]:
    return [e.tool for e in cap.events if getattr(e, "type", None) == "tool_start"]


def _score(q: dict[str, Any], out: ResearchOutput, tools: list[str]) -> dict[str, Any]:
    """YOU WRITE THIS. Score one answer. Return the dict described below.

    Inputs:
      q      one golden query: expected_ids, forbidden_ids, must_flag
      out    the agent's ResearchOutput (out.sources, out.findings, out.flags)
      tools  tool names called, in order

    Steps:
      1. cited = the set of every out.sources[i].id
      2. recall    = |cited ∩ expected| / |expected|        (1.0 if expected is empty)
      3. missed    = sorted(expected - cited)
      4. checks (each a bool):
           "searched"     "ticket_search" in tools
           "recall"       recall >= 0.8
           "no_forbidden" cited ∩ forbidden_ids is empty
           "no_leak"      cited ∩ _OTHER_TENANT_IDS is empty      ← must ALWAYS be true
           "flag"         bool(out.flags) — only when q["must_flag"] is true
           "refs_valid"   every finding.source_ref is in cited    (ADR 0002 metric)

    Return:
      {"checks": {...}, "recall": round(recall, 2), "missed": missed,
       "cited": sorted(cited)}
    """
    cited = {s.id for s in out.sources}
    expected = set(q["expected_ids"])
    forbidden = set(q.get("forbidden_ids", []))

    recall = len(cited & expected) / len(expected) if expected else 1.0
    missed = sorted(expected - cited)

    checks: dict[str, bool] = {
        "searched": "ticket_search" in tools,
        "recall": recall >= 0.8,
        "no_forbidden": not (cited & forbidden),
        "no_leak": not (cited & _OTHER_TENANT_IDS),
        "refs_valid": all(f.source_ref in cited for f in out.findings),
    }
    if q.get("must_flag"):
        checks["flag"] = bool(out.flags)

    return {"checks": checks, "recall": round(recall, 2), "missed": missed, "cited": sorted(cited)}


async def _grade_one(q: dict[str, Any], router: LLMRouter) -> dict[str, Any]:
    """Run one query, return its scorecard row. A crash is a failure, not an abort."""
    cap = _Capture()
    try:
        out = await run_agent(
            AgentRunArgs(
                query=q["query"],
                vertical=SUPPORT_VERTICAL,
                router=router,
                tenant_id=_TENANT,
                emitter=cap,
            )
        )
    except Exception as e:
        return {"id": q["id"], "error": str(e), "checks": {}, "passed": 0, "total": 1}

    tools = _tools_called(cap)
    scored = _score(q, out, tools)
    checks = scored["checks"]
    return {
        "id": q["id"],
        **scored,
        "passed": sum(checks.values()),
        "total": len(checks),
        "confidence": out.confidence,
        "cost_usd": round(out.cost_usd, 4),
        "tool_calls": len(tools),
    }


async def _run(limit: int | None, ids: list[str] | None) -> None:
    queries = json.loads(_QUERIES_PATH.read_text())
    queries = [q for q in queries if not q.get("skip")]
    if ids:
        queries = [q for q in queries if q["id"] in ids]
    if limit:
        queries = queries[:limit]

    router = create_default_router()
    rows: list[dict[str, Any]] = []
    total_cost = 0.0

    print(f"\nRunning {len(queries)} support golden queries (live Claude)...\n")
    print(f"{'':2} {'id':<26} {'score':<6} {'recall':<7} {'cost':<8} missed")
    print("-" * 90)

    try:
        for q in queries:
            r = await _grade_one(q, router)
            rows.append(r)
            total_cost += r.get("cost_usd", 0.0)
            if "error" in r:
                print(f"💥 {r['id']:<26} ERROR  {r['error'][:55]}")
                continue
            mark = "✅" if r["passed"] == r["total"] else "❌"
            print(
                f"{mark} {r['id']:<26} {r['passed']}/{r['total']:<4} {r['recall']:<7} "
                f"${r['cost_usd']:<7.3f} {r['missed']}"
            )
    finally:
        await close_db()

    graded = [r for r in rows if "error" not in r]
    passed = sum(1 for r in graded if r["passed"] == r["total"])
    mean_recall = sum(r["recall"] for r in graded) / len(graded) if graded else 0.0
    leaks = sum(1 for r in graded if not r["checks"].get("no_leak", True))
    print("-" * 90)
    print(
        f"\nPASS {passed}/{len(rows)}  ·  mean recall {mean_recall:.2f}  ·  "
        f"leaks {leaks}  ·  cost ${total_cost:.3f}\n"
    )

    _REPORTS_DIR.mkdir(exist_ok=True)
    report_path = _REPORTS_DIR / f"eval_{int(time.time())}.json"
    report_path.write_text(
        json.dumps(
            {"rows": rows, "mean_recall": mean_recall, "total_cost_usd": total_cost},
            indent=2,
        )
    )
    print(f"report → {report_path}")


def cli() -> None:
    """Console-script entry point (agentforge-eval-support)."""
    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(prog="agentforge-eval-support")
    parser.add_argument("--limit", type=int, help="run only the first N queries")
    parser.add_argument("--ids", nargs="*", help="run only these query ids")
    args = parser.parse_args()
    asyncio.run(_run(args.limit, args.ids))


if __name__ == "__main__":
    cli()
