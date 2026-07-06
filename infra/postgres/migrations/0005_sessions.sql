-- ═══════════════════════════════════════════════════════
-- Sessions (conversation threads) — group runs so the agent
-- has multi-turn context. Each run may belong to one thread.
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sessions (
  id          TEXT PRIMARY KEY,                                   -- nanoid
  tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  vertical    TEXT NOT NULL,
  title       TEXT,                                               -- first query, for the sidebar
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_sessions_ts ON sessions;
CREATE TRIGGER trg_sessions_ts BEFORE UPDATE ON sessions
  FOR EACH ROW EXECUTE FUNCTION _updated_at();

CREATE INDEX IF NOT EXISTS idx_sessions_tenant_updated
  ON sessions(tenant_id, updated_at DESC);

-- Link runs to a thread. Nullable: a run without a thread is a one-off.
ALTER TABLE runs
  ADD COLUMN IF NOT EXISTS thread_id TEXT REFERENCES sessions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_runs_thread ON runs(thread_id, enqueued_at);
