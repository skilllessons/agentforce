# AgentForge Roadmap

**Status:** Approved 2026-11-24 · **Supersedes:** the Phase 0–3 table formerly in `README.md` and `docs/phase1-week1-plan.md`

This is the working plan. Tick a task (`- [x]`) in the PR that completes it.

---

## 1. Direction

Set in the founder interview on 2026-11-24, after M2 merged.

| # | Topic | Decision |
|---|---|---|
| 1 | Customer | None yet, no deadline. **Build a valid, solid product first**, then outreach. |
| 2 | Scope | Platform for **any vertical**, with depth in **legal, insurance, support**. |
| 3 | Data sources | Customers add their own, in this order: **A upload files → B connect an app → C API / database**. |
| 4 | Hosting | **Hosted, self-serve signup.** Multi-tenant security is core. |
| 5 | Data processors | **Claude API + one embedding vendor**, both named in the privacy policy. |
| 6 | Quality | All 7 exit criteria below. Quality is never traded for speed. |

## 2. Exit criteria: the product is solid when

| # | Criterion | Target | Measured by |
|---|---|---|---|
| 1 | Right answers | recall **≥ 80%** per vertical | eval harness `recall` |
| 2 | Real citations | **100%** | eval `refs_valid` |
| 3 | No tenant leaks | **100%** | eval `no_leak` + cross-tenant API tests |
| 4 | Eval coverage | **≥ 20** golden queries per vertical | count in each `eval/golden_queries.json` |
| 5 | Fast and affordable | **≤ 60 s** and **≤ $0.25** per run | eval report `elapsed`, `cost_usd` |
| 6 | New user succeeds alone | signup → data → good answer in **≤ 10 min** | 3 test users, unassisted |
| 7 | Survives failure | clear error, **never a crash** | error-path tests per source type |

**Outreach starts when all 7 pass.**

## 3. Status

| # | Milestone | State |
|---|---|---|
| M0 | Foundation: runtime, API, worker, studio, CI, containers | ✅ PR #1, #2 |
| M1 | Zendesk connector: tickets into Postgres, cursor resume | ✅ PR #3, #4 |
| M2 | Support vertical: `ticket_search`, tenant context, evals | ✅ PR #4 |
| **M3.0** | **Staging deploy** (EKS lite, private, us-west-1) | ⬅ in progress (infra proven 2026-11-25) |
| M3 | Retrieval core | after M3.0 |
| V | Validation track: 15 interviews + 1 advisor | in parallel with M3.0–M5 |
| MT | Threads + multi-agent workspace | after M5 |

M2 baseline (first 3 support evals): 3/3 pass, mean recall 0.96, 0 leaks, ~$0.52 per run on `claude-opus-4-7`.

## 4. How to read the tasks

```
- [ ] **M3.4** Task — done when <check> · `owner`
```

| Owner | Meaning |
|---|---|
| `you` | Load-bearing code: the founder types it, Claude explains first and reviews after |
| `claude` | Scaffolding: Claude writes it |
| `decide` | A founder decision, usually recorded as an ADR |

One milestone = one branch `mN-<name>` = one PR. Run the evals at the end of every milestone and record the numbers here.

**Deploy from day one:** every merge to `main` deploys to staging and runs the smoke test. Every milestone check also passes **on staging**, not just locally.

---

## 5. Use cases: insurance

> **Status: hypothesis.** Insurance is the *tentative* lead vertical (a Harvey-style model: upload documents, run workflows, get cited answers). We have no domain contacts yet. These flows must be confirmed by **15 interviews** with adjusters, underwriters and MGA/surplus-lines operations staff, and checked by **1 domain advisor**, before any workflow is built. Interview rule: if ≥ 5 people describe the same painful workflow, it becomes workflow #1; if nothing converges in ~6 weeks, fall back to support.

### Users

| Role | Day-to-day job | Their painful question |
|---|---|---|
| Claims adjuster | decides whether a claim is paid | "Is this loss covered under this policy?" |
| Underwriter | decides whether to insure a risk, and on what terms | "Does this submission fit our guidelines?" |
| Broker / agent | sells and services policies | "What's the difference between these two quotes?" |
| Compliance / ops (surplus lines) | files policies with states | "Is this filing complete for California?" |

### Flow 1: Coverage check (claims adjuster) — candidate workflow #1

```
① Upload        policy PDF (+ endorsements) + claim notice / photos / first notice of loss
② Ask           "Is this water damage claim covered?"  — or click [Run coverage check]
③ Agent works   (live trace, ~30–60 s)
                 • insuring agreement   → the covered perils
                 • exclusions           → which ones might apply
                 • endorsements         → which ones change the exclusions
                 • conditions           → notice deadline, deductible
                 • state rules if relevant (state_DOI_query)
④ Result        one card, every line cited to a page:
```

```
COVERAGE:    ⚠ Likely covered — needs review
WHY:         Sudden pipe burst = covered peril (Section I, p.4)
EXCEPTION:   Exclusion 2.c (continuous seepage >14 days) — claim says "noticed after 3 weeks"
             → may apply                                         [p.11 ↗]
ENDORSEMENT: HO 04 95 (water backup) attached → not relevant here [p.22 ↗]
CONDITIONS:  Reported in 25 days; policy requires "prompt notice" [p.9 ↗]
FLAGS:       ⚠ Seepage duration unclear — ask insured for plumber's report
             ⚠ Coverage opinion requires adjuster sign-off
DEDUCTIBLE:  $1,000                                               [p.2 ↗]
```

```
⑤ Act           [Copy to claim file]  [Draft letter to insured]  [Send to Slack / webhook]
```

- **Value:** reading a 30–80 page policy plus endorsements by hand drops from hours to minutes, with every statement linked to its page.
- **Safety:** the agent never gives a final coverage decision; it flags for a human (already a NEVER rule in the insurance prompt).

### Flow 2: Policy comparison (broker)

```
Upload quote A + quote B → [Compare coverage]
→ table: limits, deductibles, exclusions, endorsements; differences highlighted, each cell cited
→ [Export for client]
```

### Flow 3: Submission triage (underwriter)

```
Upload submission (application, loss runs) + our underwriting guidelines → [Fits appetite?]
→ ✅ / ❌ per guideline rule, each citing the guideline and the submission
→ list of missing information → [Request from broker]
```

### Flow 4: Filing compliance (surplus lines; the wedge from the 2026-08-28 research)

```
Upload policy + state filing requirements → [Ready to file in CA?]
→ checklist: required forms, disclosures, deadlines; ✅ / ❌, each cited
```

### What the flows need from the platform

| Need | Coverage | Compare | Triage | Filing | Where |
|---|---|---|---|---|---|
| PDF upload + parsing of long, multi-section documents | ✅ | ✅ | ✅ | ✅ | M5 |
| Hybrid search inside documents | ✅ | ✅ | ✅ | ✅ | M3 |
| **Page-level citations** with links | ✅ | ✅ | ✅ | ✅ | M4 + M10 |
| **Workflow:** a named task, required inputs, fixed steps, fixed output layout | ✅ | ✅ | ✅ | ✅ | not scheduled |
| Compare two documents | | ✅ | | | not scheduled |
| The customer's own rules (guidelines, requirements) | | | ✅ | ✅ | M5 (upload) |
| State rules | ✅ | | | ✅ | existing tools |

### Where these flows landed in the tasks

| Need | Tasks |
|---|---|
| Validation: 15 interviews + 1 advisor, ~3 h/week | **V.1–V.7** (runs alongside M3.0–M5) |
| Chunks keep page numbers | **M3.6** |
| Page-level citations: a `page` field on `Source` | **M4.9** |
| Long-PDF parsing: sections, endorsements, tables, pages | **M5.5** |
| Workflows: name + required inputs + fixed steps + output schema | **M9.1–M9.5** |
| Compare two documents | **M9.6** |

---

## V: Validation track (in parallel with M3.0–M5)

**Goal:** confirm the lead vertical and workflow #1 with real users before building any workflow. ~3 h/week, founder-run. See §5.

- [ ] **V.1** Interview script: "walk me through your last coverage question; what took longest; what do you search; what would you pay to skip?" No pitching — done when written in `docs/research/` · `claude`
- [ ] **V.2** Target list of 40 people: claims adjusters, underwriters, MGA / surplus-lines ops (LinkedIn, adjuster communities) — done when the list exists · `you`
- [ ] **V.3** Find 1 domain advisor (paid hours or advisory equity) to review evals and answers — done when they've agreed · `you`
- [ ] **V.4** Run 15 interviews, notes in `docs/research/interviews/` (no personal data) — done when 15 are written up · `you`
- [ ] **V.5** Synthesis: rank workflows by pain, frequency and willingness to pay — done when the ranking is in `docs/research/` · `claude`
- [ ] **V.6** Lock the lead vertical and workflow #1: if ≥ 5 interviewees share the same painful workflow it's #1; if nothing converges in ~6 weeks, fall back to support — done when recorded in §1 and §5 · `decide`
- [ ] **V.7** Advisor-written golden queries for workflow #1 (≥ 20, with expected citations) — done when the advisor signs off · `you`

---

## M3.0: Staging deploy (EKS lite, private)

**Goal:** the current system runs in AWS from now on, on **the same stack as production** (EKS + RDS + the same Helm chart and CI), so there are no deploy surprises at M7 and nothing gets built twice. Production in M7 is the same Terraform with bigger sizes.

**Decided 2026-11-24:** EKS, region **`us-west-1`**, budget **$170–200 a month**.

**Decided 2026-11-25: session staging.** The account is on the AWS free plan with **$120 of credits** (expires 2027-04-10); always-on staging would use them in ~20 days, and scale-to-zero still costs ~$125/mo (EKS control plane, NAT, ALB). So staging is **created when testing and destroyed when done**: ~20 min up, ~10 min down, ≈ $0.25 per hour while up. Staging data is wiped on every `down` (fine: no customers). The state bucket (bootstrap) is never destroyed. Move to always-on (paid plan) when there are users. If EKS turns out to be restricted on the free plan, the first `apply` fails and the account must be upgraded first.

| Item | Staging size | ~$/month |
|---|---|---|
| EKS control plane | 1 cluster | 73 |
| Node group | 1 × m7i-flex.large (free-tier eligible; scales to 0 when idle) | ~73 |
| RDS Postgres + pgvector | db.t4g.micro, 20 GB | 15 |
| Redis | in the cluster (ElastiCache off until M7) | 0 |
| NAT gateway | 1 | 33 |
| ALB | 1 | 18 |
| S3, ECR, secrets, logs | small | 10 |
| **Total running** | | **~$220** |
| Nodes scaled to 0 (not used: see session staging) | | ~$150 |
| **Session staging, ~40 h/month up** | | **~$10** |

Prices are approximate on-demand estimates; confirm in the AWS Pricing Calculator. Claude API usage is separate.

**Private until M6:** there's no auth yet, so a public URL would let anyone run the agent and spend Claude credits. The ALB only accepts traffic from an IP allowlist.

- [ ] **M3.0.1** AWS access for the CLI **without creating an Organization** (that would end the free plan and expire its credits immediately): an IAM user `agentforge-admin` with console access + MFA, CLI via `aws login --profile agentforge` (short-lived credentials; access key only as fallback); stop using root; MFA on root; a monthly budget alarm at $200 — done when `aws sts get-caller-identity --profile agentforge` works and the budget alert fires on a test · `decide`
- [x] **M3.0.2** Terraform remote state: S3 bucket (`bootstrap/`) + **S3 lockfile** (`use_lockfile`, no DynamoDB) — code done and validated; bucket created at M3.0.4 · `claude`
- [x] **M3.0.3** Terraform `staging.tfvars`: `env=staging`, `region=us-west-1`, **`az_count=2`** (the default of 3 fails: us-west-1 has 2 AZs for most accounts), 1 × t3.medium node group (min 0), RDS db.t4g.micro, ElastiCache off (add an enable toggle; RDS and ElastiCache have none today) — code done and validated; `plan` checked at M3.0.4 · `claude`
- [x] **M3.0.4** `terraform apply` staging — done when EKS, RDS (pgvector extension available), S3 and ECR exist and `kubectl get nodes` shows 1 Ready node · `you` — applied 2026-11-25: 1 node Ready, RDS 16.13 available, plan clean, destroy clean (106 resources). The pgvector check moves to the first migrate job (M3.0.8)
- [x] **M3.0.5** Helm `values-staging.yaml`: 1 replica each, Postgres → RDS, Redis in the cluster, ALB ingress with an IP allowlist — `helm lint` + `helm template` pass; pods Ready checked at M3.0.12. Also fixed a chart written for the pre-Python app: API port 3000→8000 and `/health` probes, worker HTTP probes removed (it serves no port), one worker Deployment per vertical, `runAsUser` 10001, migrations no longer skipped with RDS · `claude`
- [ ] **M3.0.5a** Cluster add-ons via Helm: AWS Load Balancer Controller (needed for the `alb` ingress) and external-secrets operator; Terraform already creates both IRSA roles — done when an `alb` Ingress gets an address and an ExternalSecret syncs · `claude` — 2026-11-25: both charts install and run; the Ingress address and ExternalSecret sync are checked at the first app deploy
- [ ] **M3.0.6** Helm CronJobs for the reaper and the Zendesk poller (none exist today) — done when both run on schedule in staging · `claude`
- [ ] **M3.0.7** Secrets (Anthropic key, DB password) from Secrets Manager into the cluster via external-secrets (Terraform already has its IAM role), never in git — done when the pods start with no plaintext secrets in the repo · `claude`
- [ ] **M3.0.8** CI: build and push the api, worker, migrate **and studio** images to ECR (add the `studio` repo; build the studio with `NEXT_PUBLIC_API_URL` set, since rewrites are baked at build time). Deploy with `helm upgrade` on merge to `main` **only when staging is up** (the job skips cleanly if the cluster doesn't exist), plus a manual "deploy now" trigger. GitHub OIDC role, no long-lived keys — done when a merge reaches a running staging automatically, and a merge with staging down passes CI · `claude`
- [ ] **M3.0.9** Smoke test after every deploy ($0): `/health` → 200; a scripted-LLM support run → `completed`; the studio home page loads — done when a failing smoke test fails the CI job · `claude`
- [ ] **M3.0.10** `make staging-up` / `make staging-down` (session staging). `down` must: uninstall the Helm release first (the ALB is created by the controller, not Terraform, and blocks VPC deletion), then `terraform destroy` everything except the state bucket. ECR `force_delete` outside prod so `destroy` doesn't fail on stored images (CI rebuilds them) — done when up → smoke test → down → up again works, and the AWS bill shows nothing left running after `down` · `claude`
- [ ] **M3.0.11** RDS automated backups (1 day while on the free plan; 7 on a paid plan) + a tested restore — done when a restore to a new instance works · `claude`
- [ ] **M3.0.12** Milestone check — done when `make staging-up` brings staging up from nothing, a merge to `main` then reaches it in ≤ 15 min with the smoke test green, the URL is unreachable from outside the allowlist, and `make staging-down` leaves nothing billing · `you`

---

## M3: Retrieval core

**Goal:** one retrieval layer that every data source plugs into, with hybrid search (keyword + embeddings). **Moves criterion:** 1.

- [ ] **M3.1** Choose the embedding vendor; Voyage AI is the default candidate — done when ADR 0003 is accepted · `decide`
- [ ] **M3.2** Search-only eval: run each golden query straight through `ticket_search`, no LLM — done when the keyword baseline (recall per query) is saved, cost $0 · `claude`
- [ ] **M3.3** CI Postgres image → `pgvector/pgvector:pg16` (CI uses `postgres:16-alpine` today) — done when CI is green with the vector extension available · `claude`
- [ ] **M3.4** Migration: `sources`, `documents`, `chunks`, with `tenant_id` on every table, an embedding `vector` column and `CREATE EXTENSION vector` — done when migrations apply cleanly on a fresh database · `you`
- [ ] **M3.5** Embedding client in `core/` behind an interface, like the LLM router — done when it's unit-tested with a fake client and has one live smoke test · `you`
- [ ] **M3.6** Chunker: size + overlap, keeps a reference back to the document **and its page numbers** — done when unit tests cover short, long, empty and multi-page input · `you`
- [ ] **M3.7** Indexer: document → chunks → embeddings, skipping unchanged content by hash — done when re-indexing the same document writes nothing · `you`
- [ ] **M3.8** Hybrid search repo function: keyword rank + vector similarity combined, always tenant-scoped — done when the isolation test passes with two tenants · `you`
- [ ] **M3.9** Generic `knowledge_search` tool (ResearchTool contract, tenant from `get_tenant()`) — done when the six-behavior test suite passes · `you`
- [ ] **M3.10** Move tickets onto documents/chunks (backfill); `ticket_search` either uses the new layer or is replaced — done when the support evals still pass · `you`
- [ ] **M3.11** Milestone check — done when the search-only eval **beats the M3.2 baseline**, especially the synonym queries · `you`

## M4: Trustworthy output

**Goal:** output correctness enforced by code, not prompt rules. Implements [ADR 0002](adr/0002-deterministic-llm-output.md). **Moves criteria:** 2, 5.

- [ ] **M4.1** Decide `sourceRef` (one id) vs `sourceRefs` (list) — done when ADR 0002 is accepted · `decide`
- [ ] **M4.2** Synthesis through a forced tool call whose schema is `ResearchOutputBody`; remove the regex extraction — done when synthesis tests pass without `_extract_json` · `you`
- [ ] **M4.3** Validator: every `sourceRef` must match a source id — done when an invalid reference fails validation in a test · `you`
- [ ] **M4.4** Sources built by code from tool results (citable-item convention: `id`, `title`, `url`, `retrievedAt`) — done when the model can no longer write a source's metadata · `you`
- [ ] **M4.5** On validation failure: one repair attempt, otherwise fail the run with the errors in `run_events` — done when both paths are tested · `you`
- [ ] **M4.6** Check the cost cap **before** synthesis (runs reach $0.60 today against a $0.50 cap) — done when no eval run exceeds its cap · `you`
- [ ] **M4.7** `--model` flag on the eval harnesses — done when the same suite runs on two models · `claude`
- [ ] **M4.8** Choose the default model from the eval cost/quality comparison — done when the default is set via config and recorded here · `decide`
- [ ] **M4.9** Page-level citations: a `page` field on `Source`, filled by code from the chunk (never written by the model) — done when every document citation in the evals has a page · `you`
- [ ] **M4.10** Milestone check — done when support evals show `refs_valid` 100%, ≤ $0.25 and ≤ 60 s per run · `you`

## M5: Upload files (source type A)

**Goal:** a customer uploads PDFs, CSVs and docs, then asks questions about them. **Moves criterion:** 7.

- [ ] **M5.1** Choose storage: Cloudflare R2 or AWS S3 (CLAUDE.md says R2, Terraform provisions S3; `aioboto3` works with both) — done when recorded in an ADR · `decide`
- [ ] **M5.2** `core/file_storage` (an empty directory today): put / get / delete, keys prefixed by tenant — done when tested against a local S3-compatible store · `you`
- [ ] **M5.3** `files` repo for the existing `files` table (migration `0004_files.sql`) — done when there's a round-trip test · `you`
- [ ] **M5.4** `POST /v1/files` (the studio already calls it and the backend route is missing), with size and type limits — done when a bad type or size returns a clear 4xx · `you`
- [ ] **M5.5** Parsers: PDF (`pdfplumber` is installed), CSV, DOCX → documents. PDFs keep **page numbers, section headings, tables and endorsements** (insurance policies run 30–80 pages) — done when each type is tested, plus a corrupt-file test and an 80-page policy test · `you`
- [ ] **M5.6** Ingest job: file → parse → M3 indexer, with status `queued / processing / ready / failed` — done when a failure records its reason · `you`
- [ ] **M5.7** Studio upload screen: progress, status, errors — done when you can upload → see ready → ask · `claude`
- [ ] **M5.8** Fix the `policy_doc_parse` `fileRef` path (it imports the missing `core.file_storage` module) — done when its test uses real storage · `claude`
- [ ] **M5.9** Milestone check — done when uploading a PDF and asking gives a cited answer, and a corrupt file gives a clear error · `you`

## MT: Threads + multi-agent workspace

**Goal:** the workspace from the wireframes (claude.ai canvas "AgentForge Workspace Wireframes", 5 screens): files attached to a thread, several bots in one thread sharing context, bot-to-bot handoffs, thread memory you can see and edit, and an Explain view on every answer. **Moves criteria:** 3 (isolation), 6 (new-user experience). **Needs:** M4 (validated output) and M5 (uploads).

**Rules (from the wireframes):** context is shared inside a thread by default, never across workspaces; every handoff is visible; handoffs are capped per message and count toward the cost cap; a bot may *suggest* a workflow, a person clicks to run it.

- [x] **MT.1** Who can approve a workflow step → **decided 2026-11-25: roles per step.** Each approval step names a role; only people with that role can approve. Start with Admin, Member, Approver; custom role names later (M6.9) · `decide`
- [x] **MT.2** Can customers build their own workflows → **decided 2026-11-25: we build, customers configure.** Customers copy a workflow and change inputs, prompts, steps on/off and approval roles; no from-scratch builder (revisit if customers ask; full automation goes to n8n/Zapier via webhook) (M9.13) · `decide`
- [x] **MT.3** Can bots start workflows on their own → **decided 2026-11-25: no, bots only suggest.** A bot shows a [Run /workflow] button and a person clicks (MT.9). Revisit a per-workflow "safe to auto-run" switch after real usage · `decide`
- [ ] **MT.4** Thread files: a `thread_files` table linked to M5 `files`; attach/detach API; every bot and workflow in the thread can read them — done when a file added mid-thread is used by the next bot answer · `you`
- [ ] **MT.5** Context assembler: thread files + earlier answers + workflow results + memory, filtered by per-bot switches (`thread_context_settings`); today only `runs.history_for_thread` exists — done when a test shows a bot with a switch off never receives that context · `you`
- [ ] **MT.6** Several bots in one message: `@a @b …` fans out to one run per bot, linked by message id; each answer keeps its own Explain and sources; optional "combine answers" — done when two bots answer one message in the studio · `you`
- [ ] **MT.7** Bot-to-bot handoff: a tool that lets a bot ask another bot a sub-question; depth limit (default 2); each handoff is a `run_events` entry and counts toward the cost cap — done when a handoff loop is stopped at the limit in a test · `you`
- [ ] **MT.8** Thread memory: a `thread_memory` table, every fact linked to the message or file it came from; removing a fact stops all bots using it — done when a removed fact never reappears in a later prompt · `you`
- [ ] **MT.9** Workflow suggestion: a bot's answer can carry a [Run /workflow] button with prefilled inputs; nothing runs until a person clicks — done when tested · `you`
- [ ] **MT.10** Explain panel on every answer: tool calls, sources, cost, time, model, replay, copy run JSON (built from `run_events`) — done when every answer in the studio opens its Explain · `claude`
- [ ] **MT.11** Studio screens from the wireframes: thread files panel, `@` / `/` picker, side-by-side multi-bot answers, handoff display, "what bots can see" settings, history & audit with filters and export — done when each wireframe screen exists in the studio · `claude`
- [ ] **MT.12** Isolation tests: per-bot switches respected; no context crosses threads or workspaces — done when added to the cross-tenant suite (M6.8) · `claude`
- [ ] **MT.13** Milestone check — done when the wireframe story (2 files → bot answer → workflow → file added → 2 bots + handoff → memory edit → audit export) runs end to end on staging · `you`

## M6: Accounts and tenancy

**Goal:** self-serve signup with strict per-tenant isolation. **Moves criterion:** 3.

- [ ] **M6.1** Choose the auth approach: our own email + password, or a hosted auth provider — done when ADR 0004 is accepted · `decide`
- [ ] **M6.2** Signup, login, workspace (tenant) creation — done when the flow is tested end to end · `you`
- [ ] **M6.3** Put `require_tenant` on every route (it has zero callers today) and remove `_TENANT = "local-dev"` from `routes/runs.py` — done when a request without a key gets 401 · `you`
- [ ] **M6.4** API keys: create/revoke UI, and update `last_used_at` (it's never updated today) — done when tested · `you`
- [ ] **M6.5** `create_run` rejects unknown verticals (today they queue forever) — done when `POST /v1/agents/nope/run` returns 404 · `you`
- [ ] **M6.6** Rate limits from `tenants.rate_limit_per_min` (exists, unused) + CORS — done when going over the limit returns 429 · `you`
- [ ] **M6.7** Per-tenant daily cost cap from `tenants.daily_cost_cap_usd` (exists, unused) — done when going over the cap is rejected · `you`
- [ ] **M6.8** Cross-tenant API tests: every route, two tenants — done when every route is covered · `claude`
- [ ] **M6.9** Workspace roles: Admin, Member, Approver (from MT.1), assigned per person; custom role names later — done when only an Approver can approve a step in a test · `you`
- [ ] **M6.10** Milestone check — done when `no_leak` is 100% across the API tests and every eval · `you`

## M7: Production launch (scale up)

**Goal:** a production environment from the same Terraform and Helm chart as staging, with bigger sizes (more nodes, larger RDS, ElastiCache on, NAT per AZ), then open public signup. Nothing new to build at the cluster layer: staging has run on it since M3.0.

- [ ] **M7.1** Size production and apply the existing Terraform (`infra/terraform/`: EKS, RDS, ElastiCache, S3, IAM) — done when production is up and its cost is recorded here · `decide`
- [ ] **M7.2** `values-prod.yaml`: Postgres → RDS (with pgvector), Redis → ElastiCache, ALB ingress, more than one replica — done when every pod is Ready on EKS · `claude`
- [ ] **M7.3** Promotion pipeline: staging is automatic, production is a manual approval of the same image — done when a promote deploys the image that staging tested · `claude`
- [ ] **M7.4** Monitoring + alerts: failed runs, cost, latency — done when an alert fires on a test failure · `claude`
- [ ] **M7.0** AWS Organization + IAM Identity Center (SSO) for team access, replacing the M3.0 IAM user. **Deferred to launch on purpose:** creating an Organization moves the account to pay-as-you-go and expires free-plan credits immediately — done when people sign in through SSO and the IAM user is removed · `decide`
- [ ] **M7.5** Privacy policy + terms naming Anthropic and the embedding vendor — done when published · `decide`
- [ ] **M7.6** Milestone check — done when a public signup → upload → question completes in production · `you`

## M8: Connect an app (source type B)

**Goal:** customers connect Zendesk, Google Drive and SharePoint from the UI. **Moves criterion:** 7.

- [ ] **M8.1** Per-tenant connector credentials, encrypted (Zendesk credentials are global env vars today) — done when two tenants poll their own Zendesk accounts · `you`
- [ ] **M8.2** Zendesk connect flow in the UI (OAuth) → a poller per tenant — done when connecting needs no env vars · `you`
- [ ] **M8.3** Ticket comments → documents (only the first message is indexed today) — done when an eval query that's only answerable from a reply passes · `you`
- [ ] **M8.4** Google Drive connector — done when docs sync and are searchable · `you`
- [ ] **M8.5** SharePoint connector — done when docs sync and are searchable · `you`
- [ ] **M8.6** Sync scheduler + per-source status and errors in the UI — done when broken credentials show a clear error · `you`
- [ ] **M8.7** Milestone check — done when Zendesk + Drive are connected from the UI and give cited answers · `you`

## M9: Workflows + vertical depth

**Goal:** Harvey-style workflows (a named task with fixed inputs, steps and a cited result card) for the lead vertical, plus every vertical at the quality bar. Workflow #1 is whatever **V.6** locks; the coverage check (§5 Flow 1) is the current candidate. **Moves criteria:** 1, 4.

- [ ] **M9.1** Workflow definition: name, required inputs (e.g. policy + claim), fixed steps, output schema — done when one workflow is defined as data, not code branches, and tested · `you`
- [ ] **M9.2** Workflow runner: runs the steps through the agent loop and validates the output schema (reuses M4) — done when a schema-invalid result fails the run · `you`
- [ ] **M9.3** Workflow UI: pick a workflow → fill input slots (upload) → live trace → result card with page links → actions (copy, draft, webhook) — done when the §5 Flow 1 card renders from a real run · `claude`
- [ ] **M9.4** Workflow #1 (from V.6) — done when its V.7 advisor evals reach recall ≥ 80% and `refs_valid` 100%, and the advisor approves 10 sample results · `you`
- [ ] **M9.5** Workflow #2 (next in the V.5 ranking) — done the same way as M9.4 · `you`
- [ ] **M9.6** Compare two documents (needed by policy comparison, §5 Flow 2) — done when a two-quote comparison cites both documents per row · `you`
- [ ] **M9.7** Insurance: move tools and prompt onto M3 retrieval; decide what happens to the `ISO_forms_search` stub — done when the decision is recorded · `decide`
- [ ] **M9.8** Insurance: ≥ 20 golden queries (10 exist), recall ≥ 80% — done when the eval report is recorded · `you`
- [ ] **M9.9** Support: recall ≥ 80% on hybrid search (20 golden queries already exist) — done when the eval report is recorded · `you`
- [ ] **M9.10** Legal: system prompt, domain tools, ≥ 20 golden queries — done when recall ≥ 80%. **Lower priority** while insurance leads · `you`
- [ ] **M9.11** Human approval step: the run pauses, only the roles from MT.1 can approve / request info / reject, the note is saved to history — done when an unapproved run never continues · `you`
- [ ] **M9.12** Step controls: retry one step, or edit a step's input and rerun from there; workflow and bot versions pinned per run — done when a rerun keeps the earlier steps' outputs and history shows both · `you`
- [ ] **M9.13** Configurable workflows (from MT.2): a customer copies a workflow and edits inputs, prompts, steps on/off and approval roles; each change is a new version — done when a customised copy runs and history shows its version · `you`
- [ ] **M9.14** Milestone check — done when the lead vertical's workflows and all evaluated verticals show recall ≥ 80% and `refs_valid` 100% · `you`

## M10: Polish + new-user test

**Goal:** someone who has never seen the product succeeds alone. **Moves criterion:** 6.

- [ ] **M10.1** Onboarding flow: signup → add data → first question — done when there's no dead end · `claude`
- [ ] **M10.2** Clickable citations → a source viewer showing the cited passage — done when every citation opens its source · `claude`
- [ ] **M10.3** Empty, loading and error states across the studio — done when each one is reviewed · `claude`
- [ ] **M10.4** 10-minute test with 3 people who haven't seen the product; fix the top issues — done when 3/3 succeed alone in ≤ 10 min · `you`

## M11: API / database sources (source type C)

**Goal:** customers connect their own REST API or database. **Moves criterion:** 7.

- [ ] **M11.1** Choose the first targets (e.g. REST/JSON, Postgres) — done when recorded here · `decide`
- [ ] **M11.2** Connection form + field mapping → documents — done when a sample REST API is connected · `you`
- [ ] **M11.3** Scheduled sync + errors — done when a bad connection gives a clear error · `you`
- [ ] **M11.4** Milestone check — done when a sample API and a Postgres database both give cited answers · `you`

## Outreach

- [ ] **O.1** All 7 exit criteria pass — done when every number in section 2 is recorded here · `you`

---

## 6. Known gaps these tasks depend on

Found in the repo on 2026-11-24.

| Gap | Where | Task |
|---|---|---|
| No `vector` column or embeddings anywhere; CI Postgres lacks pgvector | migrations, `.github/workflows/ci.yml` | M3.3, M3.4 |
| `core/file_storage/` is empty; `policy_doc_parse` imports it | `core/file_storage/`, `verticals/insurance/tools/policy_doc_parse.py` | M5.2, M5.8 |
| Studio calls `POST /v1/files`; the route doesn't exist | `apps/studio/src/lib/api-client.ts` | M5.4 |
| `require_tenant` has zero callers; tenant hardcoded | `api_gateway/deps.py`, `routes/runs.py` | M6.3 |
| Unknown verticals queue forever | `routes/runs.py` → `create_run` | M6.5 |
| `rate_limit_per_min`, `daily_cost_cap_usd` exist but are unused | `tenants` table | M6.6, M6.7 |
| Cost cap not checked before synthesis | `core/runtime/loop.py` | M4.6 |
| No CronJobs for reaper/poller; no deploy job; CI doesn't build the studio image | `infra/helm`, CI | M3.0.6, M3.0.8 |
| Terraform never applied; defaults cost ~$420–450 a month; `az_count=3` fails in us-west-1; no toggle to turn RDS/ElastiCache off; remote state commented out | `infra/terraform/` | M3.0.2, M3.0.3, M7.1 |
| Zendesk credentials are global env vars | `connectors/zendesk/client.py`, `core/config.py` | M8.1 |
| Only the first ticket message is indexed | `connectors/zendesk/mapping.py` | M8.3 |
| Runs attach images only; no thread-level files | `runs.attachments` | MT.4 |
| One vertical per run; no multi-bot messages or handoffs | `routes/runs.py`, `core/runtime/loop.py` | MT.6, MT.7 |
| Thread context is previous turns only (`history_for_thread`); no memory | `core/db/repos/runs.py` | MT.5, MT.8 |
| Storage: CLAUDE.md says R2, Terraform provisions S3 | `CLAUDE.md`, `infra/terraform/main.tf` | M5.1 |
| AWS free plan: only free-tier instance types (t3.medium refused); RDS backup retention capped (7 refused) | `envs/staging/staging.tfvars` | M3.0.11, M7.1 |
