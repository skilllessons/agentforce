"""Search-only eval for the support vertical (roadmap M3.2).

Sends each golden query straight to the ticket search, with no LLM and no
agent, and scores what comes back. This isolates retrieval quality: the full
eval (run_evals.py) mixes it with the model's choices.

Run:
    uv run python -m agentforge.verticals.support.eval.run_search_evals
    uv run python -m agentforge.verticals.support.eval.run_search_evals --save-baseline

Needs Postgres with tickets seeded (`uv run python scripts/seed_tickets.py`).
Costs $0. Runs as tenant `local-dev`. The status filter stays off: picking a
status is the agent's job, so this measures raw retrieval.

`--save-baseline` also writes eval/baselines/search_keyword.json (committed):
the number hybrid search (M3.11) must beat.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from agentforge.core.db.client import close_db
from agentforge.core.db.repos import tickets as tickets_repo
from agentforge.verticals.support.eval.run_evals import _OTHER_TENANT_IDS

_DIR = Path(__file__).parent
_QUERIES_PATH = _DIR / "golden_queries.json"
_REPORTS_DIR = _DIR / "reports"
_BASELINE_PATH = _DIR / "baselines" / "search_keyword.json"
_TENANT = "local-dev"
_K = 10
_TYPES = ("synonym", "topic", "status", "flag", "none")


def query_type(query_id: str) -> str:
    """Group a golden query by its id prefix (synonym_*, status_* ...)."""
    prefix = query_id.split("_", 1)[0]
    return prefix if prefix in _TYPES else "topic"


def score(q: dict[str, Any], returned_ids: list[str]) -> dict[str, Any]:
    """Score one query's search results. Pure: no I/O.

    recall          |returned ∩ expected| / |expected|; 1.0 when nothing is expected
    false_hits      results for a query that expects none ("none" queries)
    forbidden_hits  results listed in forbidden_ids
    leaks           results that belong to another tenant
    """
    returned = set(returned_ids)
    expected = set(q["expected_ids"])
    recall = len(returned & expected) / len(expected) if expected else 1.0
    return {
        "id": q["id"],
        "type": query_type(q["id"]),
        "recall": round(recall, 2),
        "missed": sorted(expected - returned),
        "returned": returned_ids,
        "false_hits": len(returned) if not expected and q.get("search_check") != "leaks_only" else 0,
        "forbidden_hits": sorted(returned & set(q.get("forbidden_ids", []))),
        "leaks": sorted(returned & _OTHER_TENANT_IDS),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean recall overall and per query type, plus the failure counters."""

    def mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 2) if xs else 0.0

    by_type = {
        t: mean([r["recall"] for r in rows if r["type"] == t])
        for t in _TYPES
        if any(r["type"] == t for r in rows)
    }
    return {
        "mean_recall": mean([r["recall"] for r in rows]),
        "recall_by_type": by_type,
        "false_hits": sum(r["false_hits"] for r in rows),
        "forbidden_hits": sum(len(r["forbidden_hits"]) for r in rows),
        "leaks": sum(len(r["leaks"]) for r in rows),
    }


async def _run(save_baseline: bool) -> None:
    queries = [q for q in json.loads(_QUERIES_PATH.read_text()) if not q.get("skip")]
    rows: list[dict[str, Any]] = []

    print(f"\nSearch-only eval: {len(queries)} queries, keyword search, top {_K}\n")
    print(f"{'':2} {'id':<26} {'type':<8} {'recall':<7} missed")
    print("-" * 80)
    try:
        for q in queries:
            filters = q.get("search_filters", {})
            hits = await tickets_repo.search(
                _TENANT, q["query"], status= filters.get("status"), limit=_K
            )
            r = score(q, [str(h["external_id"]) for h in hits])
            rows.append(r)
            ok = r["recall"] >= 0.8 and not r["false_hits"] and not r["leaks"]
            print(f"{'✅' if ok else '❌'} {r['id']:<26} {r['type']:<8} {r['recall']:<7} {r['missed']}")
    finally:
        await close_db()

    summary = summarize(rows)
    print("-" * 80)
    print(f"\nmean recall {summary['mean_recall']}  ·  by type {summary['recall_by_type']}")
    print(
        f"false hits {summary['false_hits']}  ·  forbidden {summary['forbidden_hits']}  ·  "
        f"leaks {summary['leaks']}\n"
    )

    report = {"search": "keyword", "k": _K, "summary": summary, "rows": rows}
    _REPORTS_DIR.mkdir(exist_ok=True)
    report_path = _REPORTS_DIR / f"search_{int(time.time())}.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"report → {report_path}")
    if save_baseline:
        _BASELINE_PATH.parent.mkdir(exist_ok=True)
        _BASELINE_PATH.write_text(json.dumps(report, indent=2) + "\n")
        print(f"baseline → {_BASELINE_PATH}")


def cli() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(prog="run_search_evals")
    parser.add_argument(
        "--save-baseline", action="store_true", help=f"also write {_BASELINE_PATH.name}"
    )
    asyncio.run(_run(parser.parse_args().save_baseline))


if __name__ == "__main__":
    cli()
