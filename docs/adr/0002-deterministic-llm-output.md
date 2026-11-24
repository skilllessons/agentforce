# ADR 0002 — Deterministic parsing of LLM output

**Status:** Proposed · **Date:** 2026-11-24 · **Target:** M3

## Context

`ResearchOutput` is the product: every run returns it, and downstream flows
(n8n, Zapier, webhooks) parse it. Today its correctness depends on the model
following prompt text.

How synthesis works now (`core/runtime/synthesize.py`):

1. The prompt describes the JSON schema in prose.
2. A regex extracts the first `{` … last `}` from free text.
3. Pydantic validates the shape (`ResearchOutputBody.model_validate`).

Shape is checked; meaning is not. Observed in the first M2 support runs
(2026-11-24, runs `c7FeYIyQprnj`, `iiKIGof3ictH`):

| Defect | Example | Why it passed |
|---|---|---|
| `sourceRef` matches no source | `"sourceRef": "2, 123"` | typed `str`; any string validates |
| Fabricated source metadata | every `retrievedAt` = `2026-11-08T00:00:00` | the model writes `sources`; the real value never reaches it |
| Free-text extraction | regex `{...}` | relies on the model emitting clean JSON |

Fixing these with more prompt rules ("put one ID in sourceRef") is the wrong
layer: a rule the model can ignore is not a guarantee.

## Decision

Make output correctness a property of code, in three layers:

| Layer | Mechanism | Guarantees |
|---|---|---|
| **1. Shape** | Synthesis answers through a forced tool call whose `input_schema` is the `ResearchOutputBody` JSON schema, instead of free text | Valid JSON of the right shape, without regex extraction |
| **2. References** | Pydantic `model_validator` on `ResearchOutputBody`: every `finding.sourceRef` ∈ `{s.id for s in sources}`; reject otherwise | No citation to a source that isn't listed |
| **3. Code-built sources** | The model cites ids only. The runtime builds `sources` (title, url, retrievedAt, dataVintage) from tool results it actually received | Source metadata cannot be fabricated; a cited id must have come from a tool result in this run |

Layer 3 needs a shared convention for citable items in tool output (e.g. each
item carries `id`, `title`, `url`, `retrievedAt`). The five insurance tools
return different shapes today; they adopt the convention as part of this work.

On validation failure: one repair attempt (send the validation errors back to
the model), then fail the run with the errors in `run_events`. Never ship an
invalid `ResearchOutput`.

## Open questions (decide before implementing)

1. **One or many citations per finding.** The contract has `sourceRef: string`.
   Grouped findings ("3 tickets report double charges") want
   `sourceRefs: list[str]`. Changing it touches `schema.py`, the studio
   `ResultView`, both system prompts, and CLAUDE.md.
2. **Repair budget.** One retry costs a second synthesis call (~$0.05–0.10 at
   current model). Is that inside `maxCostUsd`?
3. **LiteLLM router.** Forced tool calls must work through the fallback router
   too, which currently flattens tool history to text.

## Consequences

- `ResearchOutput` becomes trustworthy by construction; prompt rules about
  output format can be deleted.
- Core change (`synthesize.py`, `schema.py`, loop): affects every vertical,
  needs the insurance tools updated for layer 3.
- Evals gain a hard metric: citation validity is 100% or the run fails.

## Not doing in M2

M2 ships with today's synthesis. The prompt-rule workarounds for `sourceRef`
and `retrievedAt` are **not** applied; the defects above are accepted as known
until this ADR is implemented.
