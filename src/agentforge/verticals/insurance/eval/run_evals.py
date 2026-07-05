"""Behavioral eval harness for the insurance vertical.

Runs each golden query through the REAL agent loop (live Claude) and scores
*behavior* — not facts. The checks need no domain expertise and catch the
failure modes that matter: wrong tool, missing citation, no human-review flag,
hallucination when a tool returns nothing.

Run:
    uv run agentforge-eval-insurance                 # all (non-skipped) queries
    uv run agentforge-eval-insurance --limit 3       # first 3 (cheap demo)
    uv run agentforge-eval-insurance --ids naic_acc_mdl880 iso_ho_flood

Needs ANTHROPIC_API_KEY (live) and, optionally, Redis for the tool cache.
NOT Postgres — eval calls run_agent directly, no queue/worker/DB.

Each run prints a scorecard and writes a JSON report under eval/reports/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from agentforge.core.llm.factory import create_default_router
from agentforge.core.llm.types import LLMRouter
from agentforge.core.runtime.loop import AgentRunArgs, run_agent
from agentforge.verticals.insurance import INSURANCE_VERTICAL

_DIR = Path(__file__).parent
_QUERIES_PATH = _DIR / "golden_queries.json"
_REPORTS_DIR = _DIR / "reports"

_FLAG_KEYWORDS = ("review", "attorney", "underwriter", "counsel", "verify")


class _Capture:
    """Minimal emitter that records the run's event stream."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    def emit(self, event: Any) -> None:
        self.events.append(event)


def _tools_called(cap: _Capture) -> list[str]:
    return [e.tool for e in cap.events if getattr(e, "type", None) == "tool_start"]


async def _grade_one(q: dict[str, Any], router: LLMRouter) -> dict[str, Any]:
    """Run one query, return its scorecard row."""
    cap = _Capture()
    try:
        out = await run_agent(
            AgentRunArgs(
                query=q["query"],
                vertical=INSURANCE_VERTICAL,
                router=router,
                tenant_id="eval",
                emitter=cap,
            )
        )
    except Exception as e:  # a crash IS a failure — record it, don't abort the suite
        return {"id": q["id"], "error": str(e), "checks": {}, "passed": 0, "total": 1}

    tools = _tools_called(cap)
    blob = json.dumps(out.model_dump(by_alias=True, mode="json")).lower()
    flags_text = " ".join(out.flags).lower()

    checks: dict[str, bool] = {"schema": bool(out.summary)}
    if q.get("expected_tool"):
        checks["tool"] = q["expected_tool"] in tools
    if q.get("must_cite"):
        checks["cite"] = all(c.lower() in blob for c in q["must_cite"])
    if q.get("must_flag_human_review"):
        checks["human_flag"] = any(k in flags_text for k in _FLAG_KEYWORDS)

    return {
        "id": q["id"],
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "confidence": out.confidence,
        "cost_usd": round(out.cost_usd, 4),
        "tools": tools,
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

    print(f"\nRunning {len(queries)} golden queries (live Claude)...\n")
    print(f"{'':2} {'id':<28} {'score':<7} {'conf':<7} {'cost':<8} checks")
    print("-" * 90)

    for q in queries:
        r = await _grade_one(q, router)
        rows.append(r)
        total_cost += r.get("cost_usd", 0.0)
        if "error" in r:
            print(f"💥 {r['id']:<28} ERROR    {r['error'][:50]}")
            continue
        mark = "✅" if r["passed"] == r["total"] else "❌"
        score = f"{r['passed']}/{r['total']}"
        print(
            f"{mark} {r['id']:<28} {score:<7} {r['confidence']:<7} "
            f"${r['cost_usd']:<7.3f} {r['checks']}"
        )

    passed = sum(1 for r in rows if "error" not in r and r["passed"] == r["total"])
    print("-" * 90)
    print(f"\nPASS {passed}/{len(rows)} queries fully passed  ·  total cost ${total_cost:.3f}\n")

    _REPORTS_DIR.mkdir(exist_ok=True)
    report_path = _REPORTS_DIR / f"eval_{int(time.time())}.json"
    report_path.write_text(json.dumps({"rows": rows, "total_cost_usd": total_cost}, indent=2))
    print(f"report → {report_path}")


def cli() -> None:
    """Console-script entry point (agentforge-eval-insurance)."""
    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(prog="agentforge-eval-insurance")
    parser.add_argument("--limit", type=int, help="run only the first N queries")
    parser.add_argument("--ids", nargs="*", help="run only these query ids")
    args = parser.parse_args()
    asyncio.run(_run(args.limit, args.ids))


if __name__ == "__main__":
    cli()
