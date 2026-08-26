---
name: new-connector
description: Build or change an AgentForge research tool end to end — pin the ResearchTool contract, follow the eight-part module skeleton, keep _INPUT_SCHEMA and _Input from drifting, register at all six touch points, write the six-assertion test suite. Use when adding a data source, editing a tool's schema, TTL, or error strings, or reviewing a tool diff. Derived from the five live insurance tools.
---

# New Connector

A connector is the only way domain data enters AgentForge, and the five live tools in `src/agentforge/verticals/insurance/tools/` share one skeleton exactly. Follow it — divergence here is not a style question, it costs cache hits and LLM routing accuracy.

This skill produces the plan and the review checklist, not the finished module: under teach-mode you type `_Input`, `_call`, and the tests. For a one-word description edit, skip to section 4.

---

## 1. Pin the Contract Before the Code

**Three facts decide the whole module. Settle them before writing a line.**

- **`ToolResult` is the only return type, on every path.** `data`, `error`, `sourceUrl`, `retrievedAt`, `rawResponse`, `fromCache` — defined in `src/agentforge/core/tools/protocol.py`.
- **`retrievedAt` is required and has no default.** Every `return`, including the validation-failure and timeout paths. Use the camelCase alias — the model has no `populate_by_name`, so `retrieved_at=` raises.
- **Tools never raise.** The loop gathers all tool calls with `asyncio.gather`; one escaped exception kills the entire run, not just that call.
- **Pick the TTL from the data's volatility**, not from a hunch:

| Data class | `cache_ttl_seconds` | Live example |
|---|---|---|
| Market / news | `900` | `web_search` |
| Regulatory portals | `21_600` | `state_DOI_query` |
| Static forms, company codes | `86_400` | `ISO_forms_search`, `NAIC_lookup` |
| Per-file content | `0` | `policy_doc_parse` — callers cache by file hash |

**Gate before writing `_call`:** Can you name the `sourceUrl`, the `retrievedAt` on the *error* path, and the TTL tier? If any is fuzzy, resolve it first — a tool the loop cannot cite is a tool the vertical cannot use.

---

## 2. Follow the Eight-Part Skeleton

**Same order, every file. A reader should be able to diff two tools and see only domain logic.**

```
1. Module docstring        — the source, and its status (live / stub / pending decision)
2. class _Input(BaseModel) — enforcement; camelCase via Field(alias=...)
3. _INPUT_SCHEMA           — what the LLM sees; camelCase; "additionalProperties": False
4. _OUTPUT_SCHEMA          — loose, documentation only, NEVER sent to the LLM
5. _now_iso()              — duplicated verbatim in all five tools; keep it that way
6. async def _call(input_) — validate, try/except, return ToolResult
7. class _XxxTool          — plain class, class-level attrs, `async def call` delegates
8. xxx_tool = _XxxTool()   — module singleton, the only public name
```

`_now_iso` being copied five times is correct under surgical-changes discipline — it graduates to a shared helper at tool #8, not before. `_OUTPUT_SCHEMA` is never passed to the router; it documents the shape for humans.

**Gate before moving on:** Does every branch of `_call` return a `ToolResult` carrying `retrievedAt`? A bare `raise`, or a `return None`, is a defect — not an edge case.

---

## 3. Keep the Two Schemas From Drifting

**`core/tools/validate.py` does not validate against `_INPUT_SCHEMA`. It calls `model_validate()`.**

So `_INPUT_SCHEMA` (what the model is told) and `_Input` (what actually enforces) are maintained in parallel and drift **silently** — the model sends a field the tool ignores, and nothing errors. Two camelCase strategies exist in-tree; only one survives contact with the cache:

| Approach | Where | Verdict |
|---|---|---|
| `Field(alias="formNumber")` | `iso_forms_search.py:22-24`, `policy_doc_parse.py` | **Use this.** One canonical input shape. |
| Manual dict remap before validation | `web_search.py:45-47`, `state_doi_query.py` | Avoid. `{"maxResults": 5}` and `{"max_results": 5}` hash to two different cache keys for one logical query — see `src/agentforge/core/tools/cache.py`. |

Read env inside `_call()`, never at module level: `naic_lookup.py:58-60` reads `AGENTFORGE_USER_AGENT` at import time, which makes it unmockable in tests.

**Gate before commit:** Diff the property names and enums in `_INPUT_SCHEMA` against `_Input`'s field aliases. A name in one and not the other is a silent runtime bug — reconcile before you test.

---

## 4. Register in All Six Places

**A tool that isn't registered is invisible; a tool registered in five places breaks the suite.**

1. The module itself — `src/agentforge/verticals/<v>/tools/<name>.py`
2. `TOOLS` in `src/agentforge/verticals/<v>/__init__.py`
3. The `TOOLS AVAILABLE` block in `src/agentforge/verticals/<v>/system_prompt.py` — the `description` string is duplicated verbatim from the tool class. This is a live drift hazard, and the model routes on the prompt copy.
4. `tests/<v>/test_<name>.py`
5. The tool-name set asserted at `tests/core/test_agent_loop_smoke.py:185-191` — stale set, red suite.
6. Credentials only: `.env.example`, the domain section of `src/agentforge/core/config.py`, and the `env_clean` tuple at `tests/conftest.py:48`.

Do **not** wire into `src/agentforge/core/tools/registry.py`. `ToolRegistry` is dead code — nothing imports it. Registration is the `TOOLS` list.

**Gate before running tests:** Is the smoke-test name set updated, and does `TOOLS AVAILABLE` quote the new description verbatim? The model will not route to a tool it cannot see.

---

## 5. Test the Six Behaviors

**Patch `httpx.AsyncClient` in the tool's own module namespace. Call the singleton directly.**

Calling `xxx_tool.call({...})` bypasses `with_cache`, so no Redis is needed. `tests/insurance/test_naic_lookup.py` is the reference. `respx` is an installed dev dependency with zero usages — don't introduce it in one tool's suite.

- Happy path — assert the exact normalized dict.
- A filter or variant input — proves the parameters reach the request.
- Empty result → structured null with a `notice`, still `success`.
- Non-200 → `data is None` and the status code appears in `error`.
- Timeout → `"timed out"` in `error.lower()`.
- A non-async contract test on `cache_ttl_seconds`.

`asyncio_mode = "auto"` (no marker needed) and `filterwarnings = ["error"]` — a warning fails the test.

**Gate before claiming done:** Is `uv run pytest tests/<vertical> -q` green, and does the timeout assertion match the tool's *actual* timeout string? A copied "timed out after 10s" against an 8-second timeout passes for the wrong reason.

---

## How to know it's working

- A new tool's diff touches six files and nobody has to ask which.
- `git diff` on the tool module shows only domain logic — the scaffolding is identical to its neighbours.
- No run has ever died from a tool raising.
- Cache hit rate is what you'd predict from the TTL tier.

## Tradeoff note

This skill is deliberately conservative: it documents the pattern the five live tools actually follow, including the duplication (`_now_iso`) and the known warts (parallel schemas, hand-copied descriptions). It optimizes for a reviewable diff over an elegant one. When the count reaches roughly a dozen tools, or a customer needs to add a source without a code deploy, the right move is to promote this skeleton to a declarative connector spec — and that is an ADR, not an edit to this file.
