-- ═══════════════════════════════════════════════════════
-- Per-run model override. NULL = use the vertical/platform default.
-- ═══════════════════════════════════════════════════════

ALTER TABLE runs
  ADD COLUMN IF NOT EXISTS model TEXT;
