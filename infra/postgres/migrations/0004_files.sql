-- ═══════════════════════════════════════════════════════
-- Files index — metadata for objects uploaded via /v1/files.
-- The bytes live in S3/R2 (see packages/core/file-storage); this row tracks
-- ownership, content-type, size, and TTL for cleanup.
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS files (
  file_id        TEXT PRIMARY KEY,                 -- storage key (e.g. "tenant_x/2026-05-08/abc...")
  tenant_id      TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  kind           TEXT NOT NULL,                    -- image | pdf | audio | text
  content_type   TEXT NOT NULL,
  filename       TEXT,
  size_bytes     BIGINT NOT NULL,
  sha256         TEXT,
  metadata       JSONB NOT NULL DEFAULT '{}',
  expires_at     TIMESTAMPTZ,                      -- nullable; cleanup job purges past TTL
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_files_tenant_created ON files(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_files_expiring       ON files(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_files_sha256         ON files(sha256) WHERE sha256 IS NOT NULL;
