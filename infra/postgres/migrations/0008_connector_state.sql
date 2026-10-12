-- ═══════════════════════════════════════════════════════
-- Where each connector left off.
--
-- A poller is a CronJob: it starts, drains, exits. The resume pointer has to
-- outlive the process or every run re-fetches the entire history and burns the
-- source's rate limit doing it.
--
-- One row per changelog, not per connector. Zendesk exposes independent
-- incremental streams (tickets, users, organizations) that sit at different
-- positions; sharing one row means the last poller to run overwrites the
-- others' bookmarks and they re-scan forever, silently.
--
-- `cursor` is opaque — base64 for Zendesk, a page token elsewhere. Never parse
-- it. NULL means never polled, which is how the poller knows to backfill;
-- that is distinct from "polled, nothing new", which stores a value.
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS connector_state (
  tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  source      TEXT NOT NULL,              -- 'zendesk'
  resource    TEXT NOT NULL,              -- 'tickets' | 'users'
  cursor      TEXT,                       -- NULL = never polled → backfill
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  PRIMARY KEY (tenant_id, source, resource)
);