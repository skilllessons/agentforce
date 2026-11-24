-- ═══════════════════════════════════════════════════════
-- AgentForge — Init: extensions + helper trigger fn.
-- Idempotent. Run before any other migration.
-- ═══════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Generic updated_at trigger function — copied verbatim from job_agent style.
CREATE OR REPLACE FUNCTION _updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
