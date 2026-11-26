# ADR 0003 — Embeddings and reranking: Voyage AI

**Status:** Accepted · **Date:** 2026-11-25 · **Target:** M3 (roadmap M3.1)

## Context

M3 adds hybrid search (keyword + vector) so retrieval finds answers whose
words differ from the query ("billed more than once" vs "charged two times").
Today's `ticket_search` is keyword-only and misses these; 5 of the 20 support
golden queries are synonym queries.

Requirements:

| Need | Why |
|---|---|
| Strong retrieval quality, English first | Exit criterion 1: recall ≥ 80% per vertical |
| Hosted API, no GPUs to run | One founder; staging is created per session; images must stay small |
| Separate query vs document encoding | Retrieval models score better with it |
| Cheap at our size | Thousands of documents, not millions, through M9 |
| Domain options later | Legal and finance verticals (M9) |

## Decision

**Voyage AI for both steps: `voyage-4` embeddings (1024-dim float) and
`rerank-3` reranking.**

Facts from docs.voyageai.com (pricing, embeddings, reranker pages, read 2026-11-25):

| Model | $/1M tokens | Free tokens | Context | Notes |
|---|---|---|---|---|
| **`voyage-4`** ⭐ embed | 0.06 | 200M | 32K | dims 256/512/**1024**/2048; "general-purpose and multilingual retrieval" |
| `voyage-4-lite` embed | 0.02 | 200M | 32K | "optimized for latency and cost" |
| `voyage-4-large` embed | 0.12 | 200M | 32K | "best general-purpose … quality" |
| `voyage-law-2` embed | 0.12 | 50M | 16K | legal-vertical candidate (M9), 1024 only |
| **`rerank-3`** ⭐ rerank | 0.05 | 200M | 32K (query + one doc) | "Highest accuracy. Recommendation for most applications." |
| `rerank-3-lite` rerank | 0.02 | 200M | 32K | "Fast and cost-effective" |

API facts the code depends on:

| API | Fact |
|---|---|
| Embeddings | `input_type`: `document` when indexing, `query` when searching |
| Embeddings | ≤ 1,000 texts and ≤ 320K tokens per request (`voyage-4`) |
| Rerank | ≤ 1,000 documents, ≤ 600K tokens per request; returns `index` + `relevance_score`, sorted |
| Rerank billing | (query tokens × documents) + all document tokens |
| Batch API | 33% cheaper, 12-hour window: fine for bulk backfills (M3.10); free tokens don't apply |

How it's used:

| Choice | Value | Why |
|---|---|---|
| Model names | config `embedding_model = "voyage-4"`, `rerank_model = "rerank-3"`; never hard-coded | Same rule as the LLM router |
| Vector column | `vector(1024)` | Default size; good quality/space trade-off |
| Stored per chunk | `embedding_model` next to the vector | A model change is detectable; vectors from two models are never compared |
| Clients | `core/` interfaces (`EmbeddingClient`, `Reranker`) with Voyage implementations (M3.5) | Swap vendor (e.g. open-source) without touching indexer or search |
| Rerank failure | Fall back to the RRF order; never fail the search | Reranking is an improvement, not a dependency |
| Key | `VOYAGE_API_KEY` in `Settings`; Secrets Manager in AWS | Same path as `ANTHROPIC_API_KEY` |

**Cost estimate:**

| Item | Tokens | Cost |
|---|---|---|
| Index 10,000 tickets (~500 tokens each) | 5M | ≈ $0.30, inside the free 200M |
| One search: rerank 50 candidates × ~150 tokens + query | ≈ 8.5K | ≈ $0.0004 |
| Full support eval (20 queries) | — | < $0.01 |

## Alternatives considered

| Option | Why not (now) |
|---|---|
| OpenAI `text-embedding-3` | Paid API with no clear gain; adds a second AI vendor alongside Anthropic |
| Self-hosted open-source (BGE/E5 via fastembed or PyTorch) | Free per token and no third party sees text, but +0.2–2 GB image size, CPU load on our 2-vCPU node, and ops work. **Revisit when a customer requires "no third party sees our data"**: the `EmbeddingClient` interface makes this a ~1-day swap |
| No reranker in v1 | Cheaper by ~$0.0004/search, but the reranker is the strongest single quality lever and gives a calibrated score for "no results" queries |
| `voyage-4-large` / `rerank-3-lite` | First things to try if the eval shows quality or latency problems |

## Consequences

- **Voyage AI processes customer text.** The privacy policy and terms (M7.5) must name it. The docs pages read for this ADR **do not state a data-retention or training-on-data policy**: verify Voyage's terms before any real customer data is indexed.
- Changing embedding model or dimension means **re-embedding everything** (cheap at our size, but a migration). The per-chunk `embedding_model` makes it detectable.
- The search-only eval (M3.2 baseline → M3.11) decides whether this is good enough, reported **with and without rerank**. If recall misses the target, try `voyage-4-large` before reconsidering the vendor.
- New dependency: the `voyageai` SDK or plain `httpx`, decided in M3.5.

## Open questions

1. Voyage's data retention / training policy for API inputs: verify before production.
2. Legal vertical (M9): `voyage-law-2` vs `voyage-4`, settled by that vertical's evals.

See also: `docs/design/retrieval.md` (the full retrieval design).
