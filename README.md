# AgentForge

**Vercel for research agents.** Launch domain-specific deep research agents in minutes.
Plug into any flow designer via REST API, SSE streaming, and webhooks.

---

## What it does

1. User picks a vertical (insurance, legal, finance, medical...)
2. Configures query, tools, and output format
3. Deploys in one click — gets a live REST API endpoint
4. Flow designers (n8n, Flowise, React Flow) consume the API

Under the hood: a custom HTTP orchestrator runs an agent loop using Claude's native
tool use API, calling domain-specific data connectors (ISO forms, Westlaw, EDGAR,
ClaimSearch, FHIR) and returning structured JSON with citations, confidence scores,
and flags for human review.

---

## Key differentiators

- **Domain data, not just web search** — ISO forms, state DOI, Verisk, Westlaw,
  EDGAR deep parse, FHIR. Not Perplexity.
- **Structured output** — `{ summary, findings[], sources[], flags[], confidence }`.
  Pipes directly into enterprise workflow systems.
- **Domain-tuned prompts** — underwriter-specific, adjuster-specific, attorney-specific
  rules baked in. Not generic AI.
- **API-first** — every vertical is a REST endpoint. Flow designers are first-class citizens.
- **No LangChain** — custom agent loop. Thin, auditable, fast.

---

## Quick start

```bash
# Install dependencies
npm install

# Set up environment (copy and fill in .env)
cp .env.example .env

# Start infrastructure (Redis, Postgres)
docker compose up -d

# Start the API server
npm run dev --workspace=packages/platform/api-gateway

# Run an insurance query
curl -X POST https://localhost:3000/v1/agents/insurance/run \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Does CGL cover a data breach for a CA SaaS company?",
    "output_format": "json",
    "max_seconds": 60
  }'
```

---

## Project structure

```
agentforge/
├── packages/
│   ├── core/               # agent runtime, tool registry, LLM router, observability
│   ├── verticals/          # domain templates (insurance, legal, finance...)
│   └── platform/           # API gateway, worker, webhook delivery
├── apps/
│   ├── studio/             # Next.js web UI
│   └── docs/               # OpenAPI-generated docs
└── infra/                  # Redis, Postgres, Terraform
```

---

## Adding a vertical

See [SKILL.md](./SKILL.md) for the full step-by-step guide Claude follows.

High level:
1. Implement tools in `packages/verticals/{name}/tools/`
2. Write system prompt in `packages/verticals/{name}/system-prompt.ts`
3. Create 20+ eval queries in `packages/verticals/{name}/eval/`
4. Run `npm run eval --workspace=packages/verticals/{name}` — must hit 80%
5. Register in `packages/platform/api-gateway/verticals.registry.ts`

---

## Current verticals

| Vertical | Status | Data sources | Avg run time |
|---|---|---|---|
| Insurance | Phase 1 — building | Tavily, State DOI, NAIC, PDF parse, ISO forms | 45s est. |
| Legal | Phase 2 — planned | CourtListener, PACER, Cornell LII, EDGAR | — |
| Finance | Phase 2 — planned | SEC EDGAR, FRED, earnings transcripts | — |
| Medical | Phase 3 — planned | PubMed, ClinicalTrials.gov, OpenFDA, SNOMED | — |

---

## For Claude sessions

Start every session with:
```
Read claude.md and SKILL.md in this project before writing any code.
```

Both files are in the project root. `claude.md` gives project context and architectural
decisions. `SKILL.md` gives the exact patterns to follow for tools, prompts, evals,
caching, and streaming.

---

## Roadmap

| Phase | Weeks | Goal |
|---|---|---|
| 0 — Foundation | 1–4 | Core agent runtime, API scaffold, Redis + OTel |
| 1 — Insurance MVP | 5–12 | 5 tools, system prompt, 5 paying customers |
| 2 — Revenue | 13–28 | Legal + Finance verticals, $20K MRR, 1 data partnership |
| 3 — Platform | 29–52 | 6+ verticals, Series A, partner SDK, $100K MRR |

---

## License

Proprietary — all rights reserved.
