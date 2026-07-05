# AgentForge — Project Context for Claude

> Paste this file at the start of every Claude session working on this project.
> Claude should read this fully before writing any code, docs, or plans.

---

## What we are building

A **platform** (not a product) for launching domain-specific deep research agents.
Think: Vercel for research agents. Users pick a vertical (insurance, legal, medical, finance...),
configure tools and prompts, deploy in one click, and get a REST API + webhook they can
plug into any flow designer (n8n, Flowise, React Flow, Zapier).

**The core insight:** Big AI gives general web search. We give gated domain data
(ISO forms, Westlaw, ClaimSearch, EDGAR deep parse, FHIR) + domain-tuned prompts +
structured JSON output that pipes into enterprise workflows. That is the moat.

---

## Current phase

**Phase 1 — Insurance MVP (Weeks 5–12)**

Active priorities in order:
1. Insurance tool implementations (5 tools — see Tools section)
2. Insurance system prompt v1 + eval dataset (30 golden queries)
3. POST /v1/agents/{vertical}/run API endpoint
4. Minimal web studio UI (vertical picker → query → result → API key)

---

## Tech stack (decided — do not suggest alternatives)

| Layer | Choice | Reason |
|---|---|---|
| LLM | Claude via Anthropic API (native tool use) | Best tool use, structured output |
| LLM fallback | LiteLLM | Model-agnostic fallback |
| Orchestrator | Custom HTTP — thin, no framework | No LangChain, no LangGraph |
| API server | Fastify (Node) or FastAPI (Python) | Fast, schema-first |
| State | Redis — namespace per tenant | Session state + tool cache |
| Long-term memory | pgvector (PostgreSQL extension) | RAG across runs |
| Observability | OpenTelemetry + Langfuse | Spans per tool call + LLM traces |
| Frontend | Next.js + React Flow | Studio UI + flow designer |
| File storage | S3-compatible (Cloudflare R2) | Raw outputs, PDFs |

---

## Repository structure

```
agentforge/
├── packages/
│   ├── core/
│   │   ├── agent-runtime/     # tool loop, stop logic, cost tracking
│   │   ├── tool-registry/     # ResearchTool interface + registration
│   │   ├── llm-router/        # Anthropic + LiteLLM wrapper
│   │   ├── output-schema/     # shared JSON output schema
│   │   └── observability/     # OTel + Langfuse wrappers
│   │
│   ├── verticals/
│   │   ├── insurance/
│   │   │   ├── tools/         # ISO, DOI, NAIC, policy-parse connectors
│   │   │   ├── system-prompt.ts
│   │   │   ├── eval/          # 30 golden queries + expected outputs
│   │   │   └── index.ts       # exports { tools, systemPrompt, outputSchema }
│   │   ├── legal/             # (Phase 2)
│   │   ├── finance/           # (Phase 2)
│   │   └── medical/           # (Phase 3)
│   │
│   └── platform/
│       ├── api-gateway/       # Fastify routes, auth, rate limiting
│       ├── run-orchestrator/  # queues runs, assigns to workers
│       ├── worker/            # executes agent loop, streams results
│       └── webhook-delivery/  # SSE + push delivery with retry
│
├── apps/
│   ├── studio/                # Next.js web studio
│   └── docs/                  # auto-generated from OpenAPI spec
│
└── infra/
    ├── redis/
    ├── postgres/
    └── terraform/
```

---

## Core interfaces (memorize these — everything builds on them)

### ResearchTool

```typescript
interface ResearchTool {
  name: string                          // snake_case, what the LLM sees in tool call
  description: string                   // prompt engineering — be specific about when to use this
  inputSchema: JSONSchema               // validated before calling
  outputSchema: JSONSchema              // normalized response shape
  call(input: unknown): Promise<ToolResult>
  cacheTtlSeconds: number               // 0 = no cache, 900 = 15min default
  estimatedCostUsd: number              // for pre-run budget check
  vertical?: string                     // optional — scope to a vertical
}

interface ToolResult {
  data: unknown                         // normalized output
  sourceUrl?: string                    // for citations — required for regulated verticals
  retrievedAt: string                   // ISO timestamp — for data freshness disclosure
  rawResponse?: unknown                 // debug only, never in final output
}
```

### Agent output (always this shape — every vertical, every query)

```typescript
interface ResearchOutput {
  summary: string                       // 2–3 sentence executive answer
  findings: Finding[]                   // ordered by relevance
  sources: Source[]                     // every source cited in findings
  flags: string[]                       // items requiring human review
  confidence: 'high' | 'medium' | 'low'
  runId: string
  elapsedSeconds: number
  toolCallCount: number
  costUsd: number
}

interface Finding {
  claim: string
  evidence: string
  sourceRef: string                     // matches Source.id
  confidence: 'high' | 'medium' | 'low'
}

interface Source {
  id: string
  title: string
  url?: string
  retrievedAt: string
  dataVintage?: string                  // e.g. "ISO form last updated 2023-01"
}
```

---

## Agent loop (core/agent-runtime)

```
1. Receive query + vertical config (tools, systemPrompt, maxSteps, maxCostUsd, maxSeconds)
2. Build initial messages array
3. LOOP (max maxSteps iterations):
   a. Call LLM with tools
   b. If stop_reason == 'end_turn' → go to step 4
   c. If stop_reason == 'tool_use' → execute tool calls in parallel where safe
   d. Check: steps exhausted? Cost exceeded? Time exceeded? → force synthesis if so
   e. Append tool results to messages
   f. Check confidence signal from model → early stop if > 0.85
4. Synthesize: final LLM call with synthesis prompt → produce ResearchOutput
5. Stream output via SSE, deliver webhook if registered
```

**Stop conditions (all hard — never skip):**
- `maxSteps` exceeded (default: 8)
- `maxCostUsd` exceeded (default: $0.50 per run)
- `maxSeconds` exceeded (default: 90s)
- LLM signals `end_turn` without pending tool calls
- Confidence > 0.85 (model self-reported in scratchpad)

---

## System prompt structure (every vertical follows this template)

```
You are a [domain] research agent. You serve [buyer personas].

DATA SOURCES AVAILABLE:
[list tools with one-line description each]

ALWAYS:
- [citation rule specific to this domain]
- [jurisdiction/scope rule]
- [evidence quality rule]
- State your confidence (high/medium/low) after each finding

NEVER:
- [legal/medical/financial advice disclaimer]
- [hallucination guard specific to this domain]
- [recency assumption guard]

OUTPUT FORMAT:
Respond ONLY with valid JSON matching this schema:
{ summary, findings[], sources[], flags[], confidence }
```

---

## API contract (do not deviate from this)

```
POST /v1/agents/{vertical}/run
  Body: { query, tools?, output_format?, webhook_url?, max_seconds?, max_cost_usd?, context? }
  Returns: { run_id, status: 'queued', stream_url, estimated_seconds }

GET  /v1/runs/{run_id}
  Returns: { run_id, status, elapsed_seconds, tool_calls, cost_usd, result: ResearchOutput }

GET  /v1/agents
  Returns: { verticals: [{ id, tools[], avg_run_seconds, avg_cost_usd }] }

POST /v1/tools/register
  Body: { name, description, endpoint, auth, input_schema, output_schema }
  Returns: { tool_id, status: 'active' }
```

Streaming: SSE on `stream_url`. Events: `tool_start`, `tool_result`, `synthesis_start`, `output`, `done`.

---

## Insurance vertical — current tools (Phase 1)

| Tool | Data source | Auth needed | Cache TTL |
|---|---|---|---|
| `web_search` | Tavily API | API key | 15 min |
| `state_DOI_query` | 50 state DOI portals | None (scrape) | 6 hours |
| `NAIC_lookup` | NAIC public data | None | 24 hours |
| `policy_doc_parse` | Uploaded PDF | None | Per-file hash |
| `ISO_forms_search` | ISO public references | None | 24 hours |

**Coming in Phase 2 (requires partnership):**
- `ISO_ClaimSearch` — Verisk partnership (in negotiation)
- `AM_Best_lookup` — AM Best API (in negotiation)

---

## Working agreement (how we collaborate)

> Behavioral discipline to reduce common LLM coding mistakes. Biases toward caution over speed.
> For trivial typo/one-liner work, exercise judgment.

### 1. Think before coding

Don't assume. Don't hide confusion. Surface tradeoffs.

- State assumptions explicitly. If uncertain about *what* to build, ask before writing code.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

**Caveat for mid-execution:** once a direction is agreed, don't pause every step for confirmation. Make the reasonable call and continue — the user will redirect if needed. Ask before *starting*, not during every tool call.

### 2. Simplicity first

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you wrote 200 lines and it could be 50, rewrite it.
- Senior-engineer check: "Would they call this overcomplicated?" If yes, simplify.

### 3. Surgical changes

Touch only what you must. Clean up only your own mess.

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it unless asked.
- When your changes create orphans, remove imports/variables/functions that *your* changes made unused. Don't remove pre-existing dead code on your own initiative.
- The test: every changed line should trace directly to the user's request.

### 4. Goal-driven execution

Define success criteria. Loop until verified.

Transform vague tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan up front:
1. [Step] → verify: [check]
2. [Step] → verify: [check]

Strong criteria let you loop independently. Weak criteria ("make it work") need constant clarification.

### 5. Teach-mode + you-write-the-major-areas (in effect)

The user is learning the system, not collecting completed files. Two rules:

**Explain before writing.** Every new file gets a "what / why / how it's used" explanation up front — purpose, design rationale, how callers consume it.

**Hand off the major areas.** For non-trivial code — anything involving domain logic, state machines, async patterns, schema design, the agent loop, tool implementations, repos with non-obvious SQL — *ask the user to write it themselves* after the explanation. Then review their code: bugs, edge cases, style. Only write directly for trivial boilerplate (re-export `__init__.py` files, obvious Pydantic models from a stated schema, repetitive test fixtures).

**Workflow for each major file:**
1. Explain what / why / how it's used.
2. Sketch function signatures and key logic in *prose* (no code).
3. User writes the code.
4. Review: point out bugs, missing edge cases, suggest improvements.
5. Move on once it's solid.

**Rule of thumb:** if the code would teach the user something new about the system, *they* type it. If it's just plumbing, Claude can type it.

### These guidelines are working if

- Diffs contain fewer unnecessary changes.
- Fewer rewrites caused by overcomplication.
- Clarifying questions come *before* implementation, not after mistakes.

---

## Rules for Claude working on this project

**Always:**
- Implement tools against the `ResearchTool` interface — no exceptions
- Keep vertical logic isolated in `packages/verticals/{name}/` — core never imports from verticals
- Write eval queries when implementing a new vertical (minimum 20 before shipping)
- Add OTel span to every tool call
- Cache tool responses in Redis with appropriate TTL
- Validate inputs against `inputSchema` before calling external APIs

**Never:**
- Suggest LangChain, LangGraph, or any agent framework — we use the custom loop
- Use generic `web_search` as the only tool for regulated vertical queries
- Hardcode model names — always use the LLM router
- Return unstructured prose — every response is `ResearchOutput` JSON
- Skip error handling on tool calls — agent loop must continue on individual tool failure

**When implementing a new tool:**
1. Define `inputSchema` and `outputSchema` first
2. Implement `call()` with try/catch — return `{ data: null, error: string }` on failure, never throw
3. Set realistic `cacheTtlSeconds` (regulatory data: 6h, market data: 15min, static forms: 24h)
4. Estimate `estimatedCostUsd` (external API cost per call)
5. Write 5 unit tests with mocked responses
6. Add to the vertical's tool registry in `index.ts`

**When writing a system prompt:**
1. List ALWAYS rules first (citation format, jurisdiction rules, evidence quality)
2. List NEVER rules second (advice disclaimers, hallucination guards)
3. Specify output JSON schema explicitly in the prompt
4. Test against 5 adversarial queries before committing

---

## What we are NOT building

- A chatbot UI (Perplexity already exists)
- A LangChain wrapper (been done, commoditized)
- A general-purpose AI assistant
- A product that competes on model quality (we use Claude's model)
- Anything that requires AI to "think" beyond the agent loop — no reasoning chains, no CoT prompting in production (it burns tokens and adds latency)
