-- ═══════════════════════════════════════════════════════
-- Tenants and API keys.
-- HMAC-derived API keys remain valid; this table enriches them with metadata
-- (caps, rate-limit overrides, suspension) and provides per-key audit.
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS tenants (
  id                  TEXT PRIMARY KEY,                   -- matches the tenantId in af_<tenant>_<sig>
  name                TEXT NOT NULL,
  email               TEXT,
  status              TEXT NOT NULL DEFAULT 'active',     -- active | suspended | deleted
  daily_cost_cap_usd  NUMERIC(10, 4) NOT NULL DEFAULT 50.0000,
  total_cost_cap_usd  NUMERIC(12, 4),
  rate_limit_per_min  INT,                                -- null = use platform default
  metadata            JSONB NOT NULL DEFAULT '{}',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_tenants_ts ON tenants;
CREATE TRIGGER trg_tenants_ts BEFORE UPDATE ON tenants
  FOR EACH ROW EXECUTE FUNCTION _updated_at();

CREATE TABLE IF NOT EXISTS api_keys (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  key_prefix        TEXT NOT NULL,                  -- first 12 chars of the visible key for lookup hints
  key_hash          TEXT NOT NULL UNIQUE,           -- sha256(api_key) hex
  name              TEXT,
  scopes            TEXT[] NOT NULL DEFAULT '{}',
  last_used_at      TIMESTAMPTZ,
  expires_at        TIMESTAMPTZ,
  revoked_at        TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_tenant_active
  ON api_keys(tenant_id) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
