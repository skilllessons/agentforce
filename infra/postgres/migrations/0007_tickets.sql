-- ═══════════════════════════════════════════════════════
-- Connector landing zone: normalized people and tickets.
--
-- Layer 2 boundary. A connector writes the source system's data into these
-- tables in a shape that is NOT source-specific; everything above (agent,
-- policy, audit) reads these columns and never the source payload. Adding a
-- second connector means a second writer, not a second schema.
--
-- Test for any future column here: would it still make sense if the source
-- were Intercom or Jira? If no, it belongs in `raw`.
-- ═══════════════════════════════════════════════════════

-- ── persons ─────────────────────────────────────────────
-- Requesters and agents. Created first: tickets reference it.

CREATE TABLE IF NOT EXISTS persons (
  id                 TEXT PRIMARY KEY,                   -- internal nanoid
  tenant_id          TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  source             TEXT NOT NULL,                      -- 'zendesk'
  external_id        TEXT NOT NULL,                      -- the source system's user id
  email              TEXT,
  name               TEXT,
  role               TEXT,                               -- 'end-user' | 'agent' | 'admin'
  group_external_id  TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- The upsert key. Without it the poller inserts a duplicate person every pass.
  CONSTRAINT persons_source_key UNIQUE (tenant_id, source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_persons_tenant_email ON persons(tenant_id, email);

DROP TRIGGER IF EXISTS trg_persons_ts ON persons;
CREATE TRIGGER trg_persons_ts BEFORE UPDATE ON persons
  FOR EACH ROW EXECUTE FUNCTION _updated_at();


-- ── tickets ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tickets (
  id                   TEXT PRIMARY KEY,                 -- internal nanoid
  tenant_id            TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  source               TEXT NOT NULL,                    -- 'zendesk'

  -- The source system's primary key (Zendesk's `id`). NOT Zendesk's own field
  -- named `external_id`, which is where a customer stashes THEIR foreign key
  -- and is almost always null. Same spelling, different meaning.
  external_id          TEXT NOT NULL,

  subject              TEXT,
  body                 TEXT,                             -- Zendesk calls this `description`;
                                                         -- it is the FIRST comment only.

  -- Nullable: an unassigned ticket is normal, and the poller can see a ticket
  -- before it has seen the person. No cascade — deleting a user must not
  -- delete ticket history.
  requester_person_id  TEXT REFERENCES persons(id),
  assignee_person_id   TEXT REFERENCES persons(id),

  -- The source system's own values. The agent's proposals live in `decisions`;
  -- nothing in this table is ever overwritten by a model.
  status               TEXT,
  priority             TEXT,
  tags                 TEXT[] NOT NULL DEFAULT '{}',
  group_external_id    TEXT,

  external_created_at  TIMESTAMPTZ,

  -- Load-bearing twice: the poller's watermark, and the optimistic-concurrency
  -- token for write-back. If this moved since we read the ticket, a human
  -- touched it and our write must abort rather than clobber.
  external_updated_at  TIMESTAMPTZ,

  -- Verbatim payload, for forensics when a mapping bug surfaces weeks later.
  -- Never read at runtime: the moment anything does `raw->>'...'`, every
  -- downstream consumer is coupled to Zendesk's JSON and this layer is pointless.
  raw                  JSONB NOT NULL,

  synced_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT tickets_source_key UNIQUE (tenant_id, source, external_id)
);

-- Poller watermark scan: "everything changed since X, newest first".
CREATE INDEX IF NOT EXISTS idx_tickets_watermark
  ON tickets(tenant_id, external_updated_at DESC);

DROP TRIGGER IF EXISTS trg_tickets_ts ON tickets;
CREATE TRIGGER trg_tickets_ts BEFORE UPDATE ON tickets
  FOR EACH ROW EXECUTE FUNCTION _updated_at();
