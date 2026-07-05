-- ═══════════════════════════════════════════════════════
-- Runs lifecycle (mirrors job_agent.applications) + event stream.
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS runs (
  id                TEXT PRIMARY KEY,                              -- nanoid run id
  tenant_id         TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  vertical          TEXT NOT NULL,
  query             TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'queued',
  -- queued | running | completed | failed | cancelled
  context           JSONB NOT NULL DEFAULT '{}',
  attachments       JSONB NOT NULL DEFAULT '[]',                   -- AttachmentRef[]
  webhook_url       TEXT,
  limits            JSONB NOT NULL DEFAULT '{}',
  result            JSONB,                                          -- ResearchOutput body
  last_error        TEXT,
  attempt_count     INT NOT NULL DEFAULT 0,
  tool_call_count   INT NOT NULL DEFAULT 0,
  cost_usd          NUMERIC(10, 6) NOT NULL DEFAULT 0,
  elapsed_seconds   NUMERIC(10, 3),
  enqueued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at        TIMESTAMPTZ,
  completed_at      TIMESTAMPTZ,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_runs_ts ON runs;
CREATE TRIGGER trg_runs_ts BEFORE UPDATE ON runs
  FOR EACH ROW EXECUTE FUNCTION _updated_at();

CREATE INDEX IF NOT EXISTS idx_runs_tenant_status      ON runs(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_runs_tenant_enqueued    ON runs(tenant_id, enqueued_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_in_flight          ON runs(status) WHERE status IN ('queued', 'running');

-- Append-only event stream — durable mirror of the Redis pub/sub channel.
-- Used to replay a stream that disconnected, and to surface per-run audit.
CREATE TABLE IF NOT EXISTS run_events (
  id          BIGSERIAL PRIMARY KEY,
  run_id      TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  tenant_id   TEXT NOT NULL,                                      -- denormalized for fast tenant queries
  kind        TEXT NOT NULL,
  -- run_start | tool_start | tool_result | attachment_resolved | attachment_skipped
  -- | synthesis_start | output | stop | error
  payload     JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_run_events_run_id     ON run_events(run_id, id);
CREATE INDEX IF NOT EXISTS idx_run_events_tenant_ts  ON run_events(tenant_id, created_at DESC);
