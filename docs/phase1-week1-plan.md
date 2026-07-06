# AgentForge — Phase 1 Week-1 Ship Plan (CLI-ready)

**Goal:** demoable, exposable Insurance MVP = auth-gated API + working studio happy path + the moat tool (`ISO_forms_search`) live.

**How to use:** run tasks in order. Each task below is a self-contained prompt — paste it into your coding CLI from the repo root. Honor `CLAUDE.md` (custom loop, `ResearchTool` interface, `ResearchOutput` JSON, LLM router, Redis cache, OTel spans, stop conditions).

**Critical path:** T1 → T2 → T3, with T4 in parallel and T5 flipped on last.

**Deferred (ceo scope call — do NOT start):** file upload + `core.file_storage`, `state_DOI_query`, 30-query eval reconciliation.

---

## T1 — SSE `/stream` route  *(head of critical path — start here)*

**Files:** `src/agentforge/platform/api_gateway/routes/runs.py`, `src/agentforge/core/db/repos/run_events.py`

> Add `GET /v1/runs/{run_id}/stream` to `routes/runs.py` returning a `StreamingResponse` (`text/event-stream`). It should tail the persisted `run_events` for that run and emit SSE events named per the API contract in CLAUDE.md: `tool_start`, `tool_result`, `synthesis_start`, `output`, `done`. Read events via the existing `run_events` repo — do not add a new store. Poll/replay from Postgres until a terminal `done`/`output` event, then close. Add an OTel span. Do not change the run-creation path.

**Done when:** curling `/v1/runs/{id}/stream` on an in-flight run yields ordered SSE events ending in `done`; event names match the contract.

---

## T2 — Studio run-submit wiring  *(depends on T1)*

**Files:** `apps/studio/src/app/api/proxy/[...path]/route.ts` (new), `apps/studio/src/lib/api-client.ts`

> The studio posts runs to `/api/proxy/...` but no Next route handler exists. Create `apps/studio/src/app/api/proxy/[...path]/route.ts` that forwards `POST`/`GET` to the backend API base (from env, e.g. `AGENTFORGE_API_URL`), passing through auth headers and streaming SSE responses back unbuffered. Verify `api-client.ts` `startRun` and the `EventSource` on `stream_url` line up with the proxied paths. Do not build file upload — leave `uploadFile`/`AttachmentInput` untouched for now.

**Done when:** a query typed in the studio creates a run and renders streamed events → final `ResearchOutput` end-to-end.

---

## T3 — `ISO_forms_search` tool  *(the moat — parallel-safe)*

**Files:** `src/agentforge/verticals/insurance/tools/iso_forms_search.py`, `src/agentforge/verticals/insurance/__init__.py`, `tests/insurance/test_iso_forms_search.py` (new)

> Replace the placeholder in `iso_forms_search.py` with a real implementation against the `ResearchTool` interface. Define `inputSchema`/`outputSchema` first. Implement `call()` with try/catch returning `{data: None, error}` — never throw. Source from a public ISO forms reference (e.g. Cornell LII / public-reference fallback per the docstring); return normalized results each with a `sourceUrl` and `retrievedAt`. Set `cacheTtlSeconds = 86400` (24h static forms) and a realistic `estimatedCostUsd`. Register the tool in the vertical's `__init__.py`. Add 5 unit tests with mocked responses covering: happy path, empty result, upstream error, input-validation failure, cache key.

**Done when:** the 5 tests pass and the insurance agent can call `ISO_forms_search` in a live run and cite `sourceUrl`.

---

## T4 — Auth on run routes  *(build anytime; enable LAST)*

**Files:** `src/agentforge/platform/api_gateway/routes/runs.py`, `src/agentforge/platform/api_gateway/deps.py`, `src/agentforge/platform/run_orchestrator/queue.py`

> Enforce tenant auth on the run routes. Add `tenant_id: str = Depends(require_tenant)` (already defined in `deps.py`) to `create_run` and `get_run`; remove the hardcoded `tenant_id="local-dev"` and thread the resolved tenant through `enqueue_run`. Keep changes surgical — no other routes.

**Done when:** unauthed request → 401; valid API key → tenant resolved from the key (not hardcoded) and used for the run. **Do not merge-enable until T2 studio testing is done** (it currently relies on `local-dev`).

---

## T5 — Stale docstring cleanup  *(trivial — ride along any commit above)*

**File:** `src/agentforge/platform/worker/loop.py` (lines ~7–9)

> Delete/replace the "SCRIPTED / do NOT wire real Anthropic" docstring — `worker/main.py` already uses the live router via `create_default_router()`. Make the docstring reflect real behavior. Nothing else.

**Done when:** docstring no longer contradicts the live loop.

---

## Verification (run after T1–T4)

- `pytest tests/` green (incl. new `test_iso_forms_search.py`).
- Manual: studio query → streamed run → `ResearchOutput` renders.
- `curl` unauthed run → 401; authed run → 200 with correct tenant.
