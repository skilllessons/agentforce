# Retrieval layer design (M3)

**Status:** decisions confirmed 2026-11-25 · **Roadmap:** M3 (criterion 1: recall ≥ 80%)
**Vendor choice:** ADR 0003

One retrieval layer that every data source plugs into: hybrid search
(keyword + vector), reranked, tenant-scoped, and returning hits that carry
their own citation data.

## 1. Decisions

| # | Decision |
|---|---|
| D1 | Embeddings: **Voyage `voyage-4`**, 1024-dim, behind an `EmbeddingClient` interface (open-source swap possible later) |
| D2 | M3 scope: **tickets only**; the data model is generic for files (M5), connectors (M8) and API/DB sources (M11) |
| D3 | Merge: **RRF** (reciprocal rank fusion) of keyword + vector lists |
| D4 | Rerank: **Voyage `rerank-3`** on the top 50 → top 10; falls back to the RRF order on failure; eval reported with and without |
| D5 | Permissions: **tenant-level** in v1; per-user ACL arrives with Drive/SharePoint (M8) |
| D6 | This doc + ADR 0003 are the design record |
| D7 | Vector search: **exact scan** in M3 (no ANN index). Add **HNSW** when one tenant passes **~50k chunks** or vector-search p95 > **100 ms** |
| D8 | Keyword index: **stored `tsv` column + GIN index** on chunks (today's `ticket_search` computes `to_tsvector` per query: a full scan) |

**Storage:** everything lives in the one Postgres (RDS in AWS) with
pgvector: text, `tsv`, vectors and metadata. Raw file bytes stay in S3.
A dedicated vector DB only earns its keep around 10M+ vectors, ~100× our
roadmap; search sits behind one repo function, so moving later is contained.

## 2. What we index

| Source | Milestone | Shape | What matters |
|---|---|---|---|
| Support tickets (Zendesk) | **M3** | short **records**, metadata-heavy | filters (status, dates), synonyms; comment threads in M8 |
| Uploaded files (PDF/DOCX/CSV) | M5 | long **documents** with pages, sections and tables | page-level citations, structure, tables kept whole |
| Drive / SharePoint / help-center | M8 | documents that change | sync, updates, deletes, per-user permissions |
| APIs / databases | M11 | structured **rows** | field mapping; filters more than semantics |

Two kinds of content (**records** and **documents**) need different
chunking, but share one data model.

## 3. Data model (columns designed in M3.4)

```
sources      one connection    tenant, kind (zendesk | upload | drive …), status, last_sync
  └ documents  one logical item  ticket #105, contract.pdf: external_id, title, url,
                                 filterable metadata, content_hash, source_updated_at
      └ chunks   searchable unit  text, position, page range, heading path,
                                  tsv (GIN), embedding vector(1024), embedding_model
```

- `tickets` (migration 0007) stays the connector's **landing zone**; `documents`/`chunks` are the **search projection** built from it.
- `tenant_id` on all three tables; every query filters on it.
- Frequently filtered fields (e.g. `status`, dates) are **real columns**, not buried in JSON.

## 4. Indexing flow

```
source change → extract text + structure → chunk → add context → embed (input_type=document)
             → upsert by content_hash (unchanged = no write) → delete stale chunks
```

| Step | Records (tickets) | Documents (files, M5) |
|---|---|---|
| Chunk | 1 chunk per ticket when short; long threads split by comment | ~500–800 tokens, ~10–15% overlap, split on headings/paragraphs, never mid-sentence, tables whole |
| Add context | prepend `Ticket #105 · open · billing · "Double charge"` | prepend `contract.pdf › 4. Termination › p.12` |
| Unchanged | same `content_hash` → write nothing | same |
| Deleted at source | delete document + chunks | same |

## 5. Search flow

```
query ─┬─ filters: tenant_id ALWAYS (+ status / date / source)
       ├─ keyword: FTS on chunks.tsv            → exact words, IDs, names
       └─ vector:  exact cosine, query embedding → meaning, synonyms
            └─ RRF merge → top 50 → rerank-3 → top 10 (+ relevance_score) → threshold → hits
```

| Golden query type (support evals) | What solves it |
|---|---|
| synonym ("money back", "locked out") | vector |
| exact ("#123", "SSO", "API key") | keyword |
| status ("still open", "already solved") | metadata filter |
| none ("shipping delays") | rerank-score threshold → empty result |
| tenant probe ("Acme") | tenant filter + isolation test |

RRF: each list contributes `1 / (60 + rank)`; sum per chunk; sort. No need to
compare keyword scores with cosine scores.

## 6. Grounding

Every hit returns `id, title, url, retrievedAt (= source_updated_at), page`
from the database. The runtime builds `sources` from hits; the model cites ids
only (ADR 0002), so a citation can't name something that wasn't retrieved.

## 7. Traps and how we handle them

| Trap | Handling |
|---|---|
| Vector filter-after-search (multi-tenant) | Not possible with exact scan (D7). When HNSW arrives: pgvector ≥ 0.8 iterative scans + an isolation test with a small tenant |
| Mixing embedding models | `embedding_model` per chunk; search filters on it |
| Always returning *something* | rerank-score threshold, so a "none" query returns an empty list |
| Stale index | upsert by `content_hash`; source deletes remove chunks |
| Reranker outage | fall back to RRF order |
| Memory (when HNSW exists) | RDS `db.t4g.micro` has 1 GB; fine to ~100k chunks; then `halfvec` or a bigger instance |

## 8. How we know it works

Search-only eval, no LLM ($0 for keyword; < $0.01 with Voyage): **recall@10
per golden query**, saved as a baseline (M3.2) and compared after hybrid
(M3.11), with and without rerank. The synonym, status and "none" queries are
the ones expected to move.

## 9. Next

1. Data model: exact columns for `sources` / `documents` / `chunks` (M3.4, written by the founder).
2. The hybrid SQL: one statement doing filter + keyword + vector + RRF (M3.8).
3. Chunking rules in detail (M3.6).
