-- ═══════════════════════════════════════════════════════
-- Retrieval layer (M3.4): sources → documents → chunks.
--
-- The search projection every data source writes into
-- (docs/design/retrieval.md). Connector landing tables such as `tickets`
-- (0007) stay the source of truth; these rows are built from them by the
-- indexer and can always be regenerated.
--
-- Vector search is an exact scan for now (design D7): no ANN index.
-- Add HNSW when a tenant passes ~50k chunks or vector p95 > 100 ms.
-- ═══════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS vector;


-- ── sources ─────────────────────────────────────────────
-- One connection a tenant added: a Zendesk account, the upload area, a Drive.

CREATE TABLE IF NOT EXISTS sources (
  id              TEXT PRIMARY KEY,                    -- internal nanoid
  tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  kind            TEXT NOT NULL,                       -- 'zendesk' | 'upload' | 'drive' ...
  name            TEXT NOT NULL,                       -- human label shown in the UI
  status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'paused', 'error')),
  last_synced_at  TIMESTAMPTZ,
  last_error      TEXT,                                -- shown to the user as-is: keep it readable
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT sources_name_key   UNIQUE (tenant_id, kind, name),
  -- Target of documents' composite FK: a document's source is in the same tenant.
  CONSTRAINT sources_tenant_key UNIQUE (tenant_id, id)
);

DROP TRIGGER IF EXISTS trg_sources_ts ON sources;
CREATE TRIGGER trg_sources_ts BEFORE UPDATE ON sources
  FOR EACH ROW EXECUTE FUNCTION _updated_at();


-- ── documents ───────────────────────────────────────────
-- One logical item: ticket #105, contract.pdf, a Drive file.

CREATE TABLE IF NOT EXISTS documents (
  id                 TEXT PRIMARY KEY,                 -- internal nanoid; what citations point to
  tenant_id          TEXT NOT NULL,
  source_id          TEXT NOT NULL,
  external_id        TEXT NOT NULL,                    -- the source's id (Zendesk ticket id, file_id ...)
  title              TEXT,
  url                TEXT,                             -- citation link; null when the source has none
  status             TEXT,                             -- source status ('open', 'solved'); null for files
  source_created_at  TIMESTAMPTZ,
  source_updated_at  TIMESTAMPTZ,                      -- freshness; becomes the citation's retrievedAt
  metadata           JSONB NOT NULL DEFAULT '{}',      -- tags, priority ...: rarely-filtered extras
  content_hash       TEXT NOT NULL,                    -- sha256 of what was chunked: unchanged → skip
  indexed_at         TIMESTAMPTZ,                      -- null until its chunks are written
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Composite FK: the database itself refuses a document whose source
  -- belongs to another tenant. Deleting a source deletes its documents.
  CONSTRAINT documents_source_fk FOREIGN KEY (tenant_id, source_id)
    REFERENCES sources (tenant_id, id) ON DELETE CASCADE,
  -- The indexer's upsert key.
  CONSTRAINT documents_external_key UNIQUE (tenant_id, source_id, external_id),
  -- Target of chunks' composite FK.
  CONSTRAINT documents_tenant_key   UNIQUE (tenant_id, id)
);

-- "Which billing tickets are still open?" is a filter, not a similarity question.
CREATE INDEX IF NOT EXISTS idx_documents_tenant_status
  ON documents (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_documents_tenant_updated
  ON documents (tenant_id, source_updated_at DESC);

DROP TRIGGER IF EXISTS trg_documents_ts ON documents;
CREATE TRIGGER trg_documents_ts BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION _updated_at();


-- ── chunks ──────────────────────────────────────────────
-- The searchable unit. Rebuilt (delete + insert) when a document changes.

CREATE TABLE IF NOT EXISTS chunks (
  id               TEXT PRIMARY KEY,                   -- internal nanoid
  tenant_id        TEXT NOT NULL,                      -- copied from the document: search filters
                                                       -- chunks without a join (FK keeps it honest)
  document_id      TEXT NOT NULL,
  position         INT  NOT NULL CHECK (position >= 0),   -- order within the document
  context          TEXT NOT NULL DEFAULT '',           -- prepended header: 'Ticket #105 · open · billing'
  content          TEXT NOT NULL,                      -- what is shown and cited
  page_start       INT,                                -- null for tickets; PDFs from M5
  page_end         INT,
  token_count      INT  NOT NULL CHECK (token_count >= 0), -- batch sizing for Voyage's limits

  -- Keyword index source (design D8). Computed by Postgres on every write.
  -- 'english' must be explicit: generated columns must be immutable, and
  -- to_tsvector(text) depends on the server's default_text_search_config.
  tsv              tsvector GENERATED ALWAYS AS (
                     to_tsvector('english', context || ' ' || content)
                   ) STORED,

  -- Null until embedded: rows are written first, vectors after. A Voyage
  -- outage then leaves keyword search working; vector search skips nulls.
  embedding        vector(1024),
  embedding_model  TEXT,                               -- never compare vectors from two models

  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chunks_document_fk FOREIGN KEY (tenant_id, document_id)
    REFERENCES documents (tenant_id, id) ON DELETE CASCADE,
  CONSTRAINT chunks_position_key UNIQUE (document_id, position),
  CONSTRAINT chunks_pages_ok CHECK (
    page_start IS NULL OR page_end IS NULL OR page_end >= page_start),
  -- A vector without its model name (or the reverse) is a bug.
  CONSTRAINT chunks_embedding_model_ok CHECK (
    (embedding IS NULL) = (embedding_model IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_chunks_tsv
  ON chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_tenant_document
  ON chunks (tenant_id, document_id);
-- No vector index (design D7): exact scan within the tenant.
