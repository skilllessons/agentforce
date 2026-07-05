# ADR 0001 — Job dispatch & execution architecture

**Status:** Accepted · **Date:** 2026-06-23

## Context

AgentForge dispatches research-agent jobs: client → submit → queue → worker →
execute (LLM + tools) → persist result. We need to choose the queue and the
worker execution model, balancing production-readiness against the cost of
operating infrastructure as a solo team at MVP stage.

The envisioned end-state (client → UI/CLI → broker → listener → isolated
execution → capture logs → write result) is sound. The open questions are
*which primitives*, and *when* to adopt the heavier ones.

## Decision

Build production-*shaped* bones now, with explicit graduation triggers to the
heavier infrastructure — do not adopt the heavy options speculatively.

### Queue: Redis now → SQS/Streams → Kafka (by trigger)

| Stage | Choice | Adopt when |
|---|---|---|
| Now (MVP) | **Redis list (LPUSH/BRPOP)** | current |
| Durability upgrade | **Redis Streams** or **SQS** (managed, DLQ) | want durable redelivery + DLQ without ops |
| Event streaming | **Kafka / MSK** | a *second independent consumer* needs the job stream (e.g. real-time analytics, audit streaming), or sustained >10k msg/s |

Kafka is explicitly **not** adopted now: job dispatch needs none of replay,
fan-out, or partitioned high-throughput yet. Swapping Redis→Kafka is an infra
substitution, not a redesign — the queue interface (`enqueue_run`/`dequeue_run`)
already abstracts it.

### Execution: worker pool now → KEDA autoscale → pod-per-job (by trigger)

| Stage | Choice | Adopt when |
|---|---|---|
| Now | **single worker** (`_drain`, run on demand) | current |
| Production | **worker pool** (`run_forever`) **+ KEDA** autoscaling on queue depth | deploy to K8s |
| Hard isolation | **pod-per-job** (K8s Job / Argo per run) | untrusted code execution, or strict per-tenant resource/security isolation (enterprise) |

Pod-per-job is **not** adopted by default: agent runs call APIs/tools (no
arbitrary code execution), so the isolation upside is small and the cost
(cold-start, scheduler churn, log aggregation) is real. Worker-pool + KEDA gives
elasticity without per-job overhead.

## Consequences

- The current Redis-queue + worker spine **is** the target shape; later changes
  are substitutions behind stable interfaces, not rewrites.
- Resilience pieces (idempotent claim ✅, stuck-run reaper, graceful shutdown,
  retry) land with the deployability track, where multiple workers make them
  load-bearing. The idempotent claim was built early as the foundation.
- Observability (structured logging ✅; OTel/Langfuse next) is provider-neutral,
  so it survives every infra swap above.

## Graduation triggers (quick reference)

- **Redis → Kafka:** a second consumer needs the job stream.
- **Worker pool → pod-per-job:** untrusted execution or hard tenant isolation.
- **`_drain` → `run_forever`:** the moment workers run as persistent pods.
