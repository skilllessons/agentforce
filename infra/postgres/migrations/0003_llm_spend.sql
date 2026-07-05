-- ═══════════════════════════════════════════════════════
-- LLM spend ledger — append-only, billing-grade.
-- Lifted from job_agent.llm_spend with tenant_id + run_id scoping.
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS llm_spend (
  id              BIGSERIAL PRIMARY KEY,
  tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  run_id          TEXT REFERENCES runs(id) ON DELETE SET NULL,
  vertical        TEXT,
  model           TEXT NOT NULL,
  route           TEXT NOT NULL,                  -- 'agent_step' | 'synthesis' | 'tool_vision' | etc.
  input_tokens    INT NOT NULL DEFAULT 0,
  output_tokens  INT NOT NULL DEFAULT 0,
  cost_usd        NUMERIC(10, 6) NOT NULL DEFAULT 0,
  cache_read_tokens INT NOT NULL DEFAULT 0,
  cache_write_tokens INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_spend_tenant_ts ON llm_spend(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_spend_run       ON llm_spend(run_id);

-- Per-tenant per-day rollup for cap checks and dashboards.
CREATE OR REPLACE VIEW llm_spend_daily AS
SELECT
  tenant_id,
  DATE_TRUNC('day', created_at AT TIME ZONE 'UTC')::date AS day,
  COUNT(*)             AS calls,
  SUM(input_tokens)    AS input_tokens,
  SUM(output_tokens)   AS output_tokens,
  SUM(cost_usd)        AS cost_usd
FROM llm_spend
GROUP BY tenant_id, DATE_TRUNC('day', created_at AT TIME ZONE 'UTC');
