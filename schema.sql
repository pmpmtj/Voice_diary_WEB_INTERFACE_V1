-- =============================================================================
-- SCHEMA: Voice Diary / Complete Database Schema (PostgreSQL)
-- =============================================================================
-- Safe re-run behavior - All-in-one database initialization
-- 
-- This comprehensive schema includes:
-- - Core ingestion catalog (emails, files, diary entries)
-- - Tag classification and management
-- - LLM usage tracking with cost analysis
-- - Google Calendar integration with token tracking
-- - Pre-populated tags for automatic diary entry classification
-- - Full-text search across all content
-- - Session and report management
--
-- Usage: Run this single file to initialize the complete database
--   psql -U your_user -d voice_diary -f schema.sql
BEGIN;

-- ---------- Extensions ----------
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- (If you plan to use unaccent later) CREATE EXTENSION IF NOT EXISTS unaccent;

-- ---------- Enums ----------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'provider') THEN
    CREATE TYPE provider AS ENUM ('gmail','gdrive','filesystem','manual','other');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'item_type') THEN
    CREATE TYPE item_type AS ENUM ('email','audio','text','file','other');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ingest_status') THEN
    CREATE TYPE ingest_status AS ENUM ('new','processed','pending_text','error','tagged');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'file_role') THEN
    CREATE TYPE file_role AS ENUM ('original','attachment','transcript','processed','thumbnail','export','other');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_type') THEN
    CREATE TYPE event_type AS ENUM ('created','reprocessed','updated','file_missing','text_extracted','summary_updated','error');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deletion_type') THEN
    CREATE TYPE deletion_type AS ENUM ('soft','hard');
  END IF;
END$$;

-- ---------- Utility: language->regconfig (inline CASE expression later) ----------
-- We will use ('english','portuguese') configs when content_language matches,
-- else fall back to 'simple'. No function needed; done inline in generated cols.

-- ---------- Accounts / Sources ----------
CREATE TABLE IF NOT EXISTS source_account (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider            provider NOT NULL,
  human_name          TEXT NOT NULL,
  external_account_id TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_source_account_provider ON source_account(provider);

-- ---------- Raw JSON blobs (verbatim metadata per provider) ----------
CREATE TABLE IF NOT EXISTS raw_json_blob (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider   provider NOT NULL,
  blob       JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_json_blob_provider ON raw_json_blob(provider);

-- ---------- Ingest runs (every 5 minutes) ----------
CREATE TABLE IF NOT EXISTS ingest_run (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_account_id UUID REFERENCES source_account(id) ON DELETE SET NULL,
  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at         TIMESTAMPTZ,
  status           TEXT,           -- e.g., 'ok','partial','failed'
  stats            JSONB           -- e.g., {"items":123,"errors":2}
);

CREATE INDEX IF NOT EXISTS idx_ingest_run_started_at ON ingest_run(started_at DESC);

-- ---------- Main "ingest_item" ----------
CREATE TABLE IF NOT EXISTS ingest_item (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_account_id  UUID REFERENCES source_account(id) ON DELETE SET NULL,
  provider           provider NOT NULL,
  external_id        TEXT,                   -- provider-stable id (gmail id, drive fileId, etc.)
  external_thread_id TEXT,                   -- e.g., gmail threadId
  ingest_run_id      UUID REFERENCES ingest_run(id) ON DELETE SET NULL,

  occurred_at        TIMESTAMPTZ NOT NULL,   -- true event time: email internalDate, capture time, etc.
  ingested_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  item_type          item_type NOT NULL,
  content_language   TEXT,                   -- 'en','pt', etc. (ISO; optional)
  status             ingest_status NOT NULL DEFAULT 'new',

  title              TEXT,                   -- subject / filename / first line
  item_subject       TEXT,                   -- email subject or equivalent metadata
  content_text       TEXT,                   -- normalized plain text (.txt you ingest)
  summary_text       TEXT,                   -- LLM written "resume" (nullable initially)

  content_sha256     TEXT,                   -- hash of content_text (optional dedup visibility)
  raw_json_ref       UUID REFERENCES raw_json_blob(id) ON DELETE SET NULL,

  bytes              BIGINT,                 -- size in bytes
  len_classif        VARCHAR,                -- length classification

  is_deleted         BOOLEAN NOT NULL DEFAULT false,
  deletion_type      deletion_type DEFAULT 'soft',  -- 'soft' (recoverable) or 'hard' (permanent)
  deleted_at         TIMESTAMPTZ,            -- timestamp when item was deleted

  -- ---------------- Search columns (generated) ----------------
  -- Weighting: title -> 'A', content_text -> 'B'
  content_tsv TSVECTOR GENERATED ALWAYS AS (
    setweight(
      to_tsvector(
        CASE
           WHEN content_language IN ('en','eng','english') THEN 'english'::regconfig
           WHEN content_language IN ('pt','por','pt-pt','pt-br','portuguese') THEN 'portuguese'::regconfig
           ELSE 'simple'::regconfig
         END,
        coalesce(title,'')
      ), 'A'
    )
    ||
    setweight(
      to_tsvector(
        CASE
           WHEN content_language IN ('en','eng','english') THEN 'english'::regconfig
           WHEN content_language IN ('pt','por','pt-pt','pt-br','portuguese') THEN 'portuguese'::regconfig
           ELSE 'simple'::regconfig
         END,
        coalesce(content_text,'')
      ), 'B'
    )
  ) STORED,

  summary_tsv TSVECTOR GENERATED ALWAYS AS (
    to_tsvector(
      CASE
         WHEN content_language IN ('en','eng','english') THEN 'english'::regconfig
         WHEN content_language IN ('pt','por','pt-pt','pt-br','portuguese') THEN 'portuguese'::regconfig
         ELSE 'simple'::regconfig
       END,
      coalesce(summary_text,'')
    )
  ) STORED,

  subject_tsv TSVECTOR GENERATED ALWAYS AS (
    to_tsvector(
      CASE
         WHEN content_language IN ('en','eng','english') THEN 'english'::regconfig
         WHEN content_language IN ('pt','por','pt-pt','pt-br','portuguese') THEN 'portuguese'::regconfig
         ELSE 'simple'::regconfig
       END,
      coalesce(item_subject,'')
    )
  ) STORED
);

-- Idempotency: same provider item cannot be inserted twice.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ingest_item_provider_external
  ON ingest_item(provider, external_id)
  WHERE external_id IS NOT NULL;

-- Helpful lookups
CREATE INDEX IF NOT EXISTS idx_ingest_item_occurred_at ON ingest_item(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingest_item_source_account ON ingest_item(source_account_id);
CREATE INDEX IF NOT EXISTS idx_ingest_item_status ON ingest_item(status);
CREATE INDEX IF NOT EXISTS idx_ingest_item_item_type ON ingest_item(item_type);
CREATE INDEX IF NOT EXISTS idx_ingest_item_lang ON ingest_item(content_language);
CREATE INDEX IF NOT EXISTS idx_ingest_item_deleted ON ingest_item(is_deleted);
CREATE INDEX IF NOT EXISTS idx_ingest_item_deletion_type ON ingest_item(deletion_type) WHERE is_deleted = true;
CREATE INDEX IF NOT EXISTS idx_ingest_item_run ON ingest_item(ingest_run_id);

-- FTS indexes
CREATE INDEX IF NOT EXISTS gin_ingest_item_content_tsv ON ingest_item USING GIN (content_tsv);
CREATE INDEX IF NOT EXISTS gin_ingest_item_summary_tsv ON ingest_item USING GIN (summary_tsv);
CREATE INDEX IF NOT EXISTS gin_ingest_item_subject_tsv ON ingest_item USING GIN (subject_tsv);

-- Fuzzy subject/title
CREATE INDEX IF NOT EXISTS trgm_ingest_item_title ON ingest_item USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS trgm_ingest_item_subject ON ingest_item USING GIN (item_subject gin_trgm_ops);

-- Optional visibility: not unique initially (you tolerate occasional dupes)
CREATE INDEX IF NOT EXISTS idx_ingest_item_content_sha ON ingest_item(content_sha256);

-- For later "soft dedup" linkage (nullable)
ALTER TABLE ingest_item
  ADD COLUMN IF NOT EXISTS duplicate_of UUID REFERENCES ingest_item(id) ON DELETE SET NULL;

-- ---------- Provider side-car: EMAIL ----------
CREATE TABLE IF NOT EXISTS email_item (
  ingest_item_id UUID PRIMARY KEY REFERENCES ingest_item(id) ON DELETE CASCADE,
  message_id     TEXT,        -- RFC 5322 Message-ID
  thread_id      TEXT,        -- Gmail threadId
  from_addr      TEXT,
  to_addrs       TEXT[],      -- arrays keep it simple for now
  cc_addrs       TEXT[],
  bcc_addrs      TEXT[],
  label_ids      TEXT[],      -- Gmail labelIds
  headers_json   JSONB,
  snippet        TEXT
);

CREATE INDEX IF NOT EXISTS idx_email_item_thread ON email_item(thread_id);
CREATE INDEX IF NOT EXISTS idx_email_item_message_id ON email_item(message_id);
CREATE INDEX IF NOT EXISTS idx_email_item_from ON email_item(from_addr);

-- ---------- Provider side-car: GDRIVE ----------
CREATE TABLE IF NOT EXISTS gdrive_item (
  ingest_item_id UUID PRIMARY KEY REFERENCES ingest_item(id) ON DELETE CASCADE,
  file_id        TEXT NOT NULL,    -- stable Drive id
  mime_type      TEXT,
  md5_checksum   TEXT,
  size_bytes     BIGINT,
  created_time   TIMESTAMPTZ,
  modified_time  TIMESTAMPTZ,
  parents        TEXT[],
  properties_json JSONB
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_gdrive_file_id ON gdrive_item(file_id);
CREATE INDEX IF NOT EXISTS idx_gdrive_mime ON gdrive_item(mime_type);
CREATE INDEX IF NOT EXISTS idx_gdrive_created ON gdrive_item(created_time);
CREATE INDEX IF NOT EXISTS idx_gdrive_md5 ON gdrive_item(md5_checksum);

-- ---------- Files linked to items ----------
CREATE TABLE IF NOT EXISTS item_file (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ingest_item_id UUID NOT NULL REFERENCES ingest_item(id) ON DELETE CASCADE,
  role           file_role NOT NULL,
  abs_path       TEXT NOT NULL,
  rel_path       TEXT,                -- relative to project download_dir
  mime_type      TEXT,
  bytes          BIGINT,
  sha256         TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_deleted     BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_item_file_item ON item_file(ingest_item_id);
CREATE INDEX IF NOT EXISTS idx_item_file_role ON item_file(role);
CREATE INDEX IF NOT EXISTS idx_item_file_sha ON item_file(sha256);
-- If later you want strict binary-dedup: uncomment next line
-- CREATE UNIQUE INDEX uq_item_file_sha ON item_file(sha256) WHERE sha256 IS NOT NULL;

-- ---------- Tags ----------
CREATE TABLE IF NOT EXISTS tag (
  id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name  TEXT UNIQUE NOT NULL,
  kind  TEXT
);

CREATE TABLE IF NOT EXISTS item_tag (
  ingest_item_id UUID NOT NULL REFERENCES ingest_item(id) ON DELETE CASCADE,
  tag_id         UUID NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
  added_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ingest_item_id, tag_id)
);

-- ---------- Sessions (multi-day reports) ----------
CREATE TABLE IF NOT EXISTS report_session (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title         TEXT NOT NULL,
  owner_user_id UUID,            -- future multi-user
  opened_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at     TIMESTAMPTZ,
  notes         TEXT
);

CREATE TABLE IF NOT EXISTS report_session_item (
  report_session_id UUID NOT NULL REFERENCES report_session(id) ON DELETE CASCADE,
  ingest_item_id    UUID NOT NULL REFERENCES ingest_item(id) ON DELETE CASCADE,
  added_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  order_index       INTEGER,
  PRIMARY KEY (report_session_id, ingest_item_id)
);

CREATE INDEX IF NOT EXISTS idx_report_session_item_order ON report_session_item(report_session_id, order_index);

-- ---------- Ingestion events / audit ----------
CREATE TABLE IF NOT EXISTS ingest_event (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ingest_item_id UUID REFERENCES ingest_item(id) ON DELETE CASCADE,
  event          event_type NOT NULL,
  message        TEXT,
  data           JSONB,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ingest_event_item ON ingest_event(ingest_item_id);
CREATE INDEX IF NOT EXISTS idx_ingest_event_created ON ingest_event(created_at DESC);

-- ---------- LLM Usage Tracking ----------
-- Tracks token usage and costs for all LLM API calls (OpenAI, etc.)
-- Used by llm_tag_classifier, llm_calendar_parser, and other LLM modules
CREATE TABLE IF NOT EXISTS llm_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Link to source item being processed
  ingest_item_id UUID REFERENCES ingest_item(id) ON DELETE CASCADE,
  
  -- LLM provider and model details
  provider TEXT NOT NULL,              -- 'openai', 'anthropic', etc.
  model TEXT NOT NULL,                 -- 'gpt-3.5-turbo', 'gpt-4', etc.
  operation TEXT NOT NULL,             -- 'tag_classification', 'calendar_parsing', etc.
  
  -- Token usage (from API response)
  prompt_tokens INTEGER NOT NULL,
  completion_tokens INTEGER NOT NULL,
  total_tokens INTEGER NOT NULL,
  
  -- Cost estimation (USD)
  prompt_cost_usd DECIMAL(10, 6),
  completion_cost_usd DECIMAL(10, 6),
  total_cost_usd DECIMAL(10, 6),
  
  -- Request metadata
  temperature FLOAT,
  max_tokens INTEGER,
  
  -- Status
  success BOOLEAN NOT NULL DEFAULT true,
  error_message TEXT,
  
  -- Audit
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_item ON llm_usage(ingest_item_id);
CREATE INDEX IF NOT EXISTS idx_llm_usage_provider ON llm_usage(provider);
CREATE INDEX IF NOT EXISTS idx_llm_usage_model ON llm_usage(model);
CREATE INDEX IF NOT EXISTS idx_llm_usage_operation ON llm_usage(operation);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage(created_at DESC);

-- ---------- Google Calendar Integration ----------
-- Extends the ingestion catalog to track calendar events created from diary entries

-- Add gcalendar to provider enum if not exists
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_enum 
    WHERE enumlabel = 'gcalendar' 
    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'provider')
  ) THEN
    ALTER TYPE provider ADD VALUE 'gcalendar';
  END IF;
END$$;

-- ---------- Table: diary_calendar_link ----------
-- Links diary entries to calendar events they generated
CREATE TABLE IF NOT EXISTS diary_calendar_link (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Source diary entry that mentioned the event
  source_diary_id UUID NOT NULL REFERENCES ingest_item(id) ON DELETE CASCADE,
  
  -- Calendar event created from it
  calendar_event_id TEXT NOT NULL,              -- Google Calendar event ID
  html_link TEXT,                               -- Direct link to event
  
  -- Insertion metadata
  insertion_status TEXT NOT NULL DEFAULT 'success',  -- success, failed, pending, cancelled
  inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  error_message TEXT,                           -- If insertion failed
  
  -- LLM parsing metadata
  llm_model TEXT,                               -- e.g., "gpt-4", "claude-3"
  llm_confidence FLOAT,                         -- Parser confidence score (0.0-1.0)
  llm_prompt_tokens INTEGER,                    -- Token usage from LLM API call
  llm_completion_tokens INTEGER,
  llm_total_tokens INTEGER,
  llm_cost_usd DECIMAL(10, 6),                  -- Estimated cost in USD
  parsed_json_ref UUID REFERENCES raw_json_blob(id),  -- LLM-generated event JSON
  
  -- API response
  api_response_ref UUID REFERENCES raw_json_blob(id), -- Full Google Calendar API response
  
  -- Audit
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_diary_calendar_link_diary ON diary_calendar_link(source_diary_id);
CREATE INDEX IF NOT EXISTS idx_diary_calendar_link_event ON diary_calendar_link(calendar_event_id);
CREATE INDEX IF NOT EXISTS idx_diary_calendar_link_status ON diary_calendar_link(insertion_status);
CREATE INDEX IF NOT EXISTS idx_diary_calendar_link_inserted ON diary_calendar_link(inserted_at DESC);

-- ---------- Table: gcalendar_event ----------
-- Stores searchable event details (denormalized for fast queries)
CREATE TABLE IF NOT EXISTS gcalendar_event (
  event_id TEXT PRIMARY KEY,                    -- Google Calendar event ID
  
  -- Core event fields (searchable)
  summary TEXT NOT NULL,                        -- Event title: "Dentist appointment"
  description TEXT,                             -- Event description
  location TEXT,                                -- "Dr. Smith's office"
  
  -- Time fields
  start_datetime TIMESTAMPTZ NOT NULL,
  end_datetime TIMESTAMPTZ NOT NULL,
  start_timezone TEXT,                          -- "Europe/Lisbon"
  end_timezone TEXT,
  
  -- Status and type
  status TEXT NOT NULL,                         -- confirmed, tentative, cancelled
  event_type TEXT,                              -- default, outOfOffice, focusTime
  
  -- People
  creator_email TEXT,
  organizer_email TEXT,
  attendees_json JSONB,                         -- Full attendees array
  
  -- Recurrence
  recurrence TEXT[],                            -- RRULE strings
  recurring_event_id TEXT,                      -- Parent event if part of series
  
  -- Additional metadata
  visibility TEXT,                              -- default, public, private
  transparency TEXT,                            -- opaque (busy), transparent (free)
  reminders_json JSONB,                         -- Full reminders structure
  ical_uid TEXT,                                -- Universal calendar identifier
  
  -- Full-text search vector (generated column)
  event_tsv TSVECTOR GENERATED ALWAYS AS (
    setweight(to_tsvector('simple', coalesce(summary,'')), 'A') ||
    setweight(to_tsvector('simple', coalesce(description,'')), 'B') ||
    setweight(to_tsvector('simple', coalesce(location,'')), 'C')
  ) STORED,
  
  -- Timestamps from Google
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  
  -- Sync metadata
  etag TEXT,                                    -- For change detection
  sequence INTEGER,                             -- Event version number
  
  -- Raw JSON reference
  raw_json_ref UUID REFERENCES raw_json_blob(id), -- Full API response for reprocessing
  
  -- Audit
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes on gcalendar_event
CREATE UNIQUE INDEX IF NOT EXISTS uq_gcalendar_event_id ON gcalendar_event(event_id);
CREATE INDEX IF NOT EXISTS idx_gcalendar_event_start ON gcalendar_event(start_datetime DESC);
CREATE INDEX IF NOT EXISTS idx_gcalendar_event_status ON gcalendar_event(status);
CREATE INDEX IF NOT EXISTS idx_gcalendar_event_creator ON gcalendar_event(creator_email);
CREATE INDEX IF NOT EXISTS idx_gcalendar_event_organizer ON gcalendar_event(organizer_email);
CREATE INDEX IF NOT EXISTS idx_gcalendar_event_ical ON gcalendar_event(ical_uid);
CREATE INDEX IF NOT EXISTS idx_gcalendar_event_recurring ON gcalendar_event(recurring_event_id);
CREATE INDEX IF NOT EXISTS gin_gcalendar_event_tsv ON gcalendar_event USING GIN(event_tsv);

-- ---------- Combined View: diary_calendar_combined ----------
DROP VIEW IF EXISTS diary_calendar_combined;
CREATE VIEW diary_calendar_combined AS
SELECT 
  i.id AS diary_id,
  i.title AS diary_title,
  i.content_text AS diary_content,
  i.occurred_at AS diary_date,
  i.content_language,
  
  dcl.id AS link_id,
  dcl.insertion_status,
  dcl.inserted_at,
  dcl.llm_confidence,
  dcl.llm_model,
  dcl.error_message,
  
  e.event_id,
  e.summary AS event_summary,
  e.description AS event_description,
  e.location AS event_location,
  e.start_datetime,
  e.end_datetime,
  e.status AS event_status,
  e.event_type,
  e.creator_email,
  e.organizer_email,
  dcl.html_link,
  e.event_tsv
FROM ingest_item i
JOIN diary_calendar_link dcl ON dcl.source_diary_id = i.id
JOIN gcalendar_event e ON e.event_id = dcl.calendar_event_id
WHERE i.is_deleted = false;

-- ---------- Canonical view: "one representative per logical item"
-- Prefer external_id; else content hash; else the row id.
-- For each key, pick earliest occurred_at (stable choice).
DROP VIEW IF EXISTS ingest_item_primary;
CREATE VIEW ingest_item_primary AS
SELECT DISTINCT ON (
  provider,
  COALESCE(external_id, content_sha256, id::text)
)
  id,
  provider,
  external_id,
  occurred_at,
  item_type,
  content_language,
  status,
  title,
  item_subject,
  content_text,
  summary_text,
  content_tsv,
  summary_tsv,
  subject_tsv,
  is_deleted
FROM ingest_item
WHERE is_deleted = false
ORDER BY
  provider,
  COALESCE(external_id, content_sha256, id::text),
  occurred_at ASC;

-- ---------- Pre-populate LLM Tag Classifier Tags ----------
-- Insert default tags for the LLM Tag Classifier module
-- These tags are used for automatic classification of diary entries
INSERT INTO tag (name, kind) VALUES 
    ('agente', 'auto-generated'),
    ('calendário', 'auto-generated'),
    ('diário', 'auto-generated'),
    ('família', 'auto-generated'),
    ('finanças', 'auto-generated'),
    ('ideias', 'auto-generated'),
    ('pessoal', 'auto-generated'),
    ('saúde', 'auto-generated'),
    ('trabalho', 'auto-generated'),
    ('viagem', 'auto-generated')
ON CONFLICT (name) DO NOTHING;

COMMIT;

-- =============================================================================
-- RECOMMENDED QUERY SNIPPETS (for your scripts)
-- =============================================================================
-- 1) Full-text search across title+content (content_tsv), and summary separately:
--   SELECT id, title, occurred_at
--   FROM ingest_item_primary
--   WHERE content_tsv @@ plainto_tsquery('english', :q)  -- or 'portuguese'
--   ORDER BY occurred_at DESC
--   LIMIT 50;

-- 2) Summary search:
--   WHERE summary_tsv @@ plainto_tsquery('english', :q);

-- 3) Recent Gmail thread:
--   SELECT ii.id, ei.thread_id, ii.title, ii.occurred_at
--   FROM ingest_item_primary ii
--   JOIN email_item ei ON ei.ingest_item_id = ii.id
--   WHERE ei.thread_id = :thread
--   ORDER BY ii.occurred_at;

-- 4) LLM Usage - Total cost by operation type:
--   SELECT operation, 
--          SUM(total_cost_usd) as total_cost,
--          COUNT(*) as api_calls,
--          SUM(total_tokens) as total_tokens,
--          AVG(total_tokens) as avg_tokens_per_call
--   FROM llm_usage
--   WHERE success = true
--   GROUP BY operation
--   ORDER BY total_cost DESC;

-- 5) LLM Usage - Cost per diary entry:
--   SELECT i.title, i.occurred_at,
--          l.operation, l.model,
--          l.total_tokens, l.total_cost_usd
--   FROM llm_usage l
--   JOIN ingest_item i ON i.id = l.ingest_item_id
--   WHERE l.created_at >= now() - interval '7 days'
--   ORDER BY l.total_cost_usd DESC
--   LIMIT 20;

-- 6) LLM Usage - Daily cost summary:
--   SELECT DATE(created_at) as date,
--          operation,
--          COUNT(*) as calls,
--          SUM(total_tokens) as tokens,
--          SUM(total_cost_usd) as cost_usd
--   FROM llm_usage
--   WHERE success = true
--   GROUP BY DATE(created_at), operation
--   ORDER BY date DESC, cost_usd DESC;

-- 7) Google Calendar - How many times did I go to the dentist last year?
--   SELECT count(*), array_agg(e.start_datetime ORDER BY e.start_datetime)
--   FROM gcalendar_event e
--   WHERE e.event_tsv @@ plainto_tsquery('simple', 'dentist')
--     AND e.start_datetime >= '2024-01-01'
--     AND e.start_datetime < '2025-01-01'
--     AND e.status = 'confirmed';

-- 8) Google Calendar - Find all diary entries that resulted in calendar events:
--   SELECT i.title, i.occurred_at, e.summary, e.start_datetime
--   FROM ingest_item i
--   JOIN diary_calendar_link dcl ON dcl.source_diary_id = i.id
--   JOIN gcalendar_event e ON e.event_id = dcl.calendar_event_id
--   WHERE dcl.insertion_status = 'success'
--   ORDER BY e.start_datetime DESC;

-- 9) Google Calendar - Search events by location:
--   SELECT e.summary, e.start_datetime, e.location
--   FROM gcalendar_event e
--   WHERE e.location ILIKE '%Dr. Smith%'
--     AND e.start_datetime >= now() - interval '1 year'
--   ORDER BY e.start_datetime DESC;

-- 10) Google Calendar - Find failed calendar insertions for retry:
--   SELECT i.title, i.content_text, dcl.error_message, dcl.inserted_at
--   FROM ingest_item i
--   JOIN diary_calendar_link dcl ON dcl.source_diary_id = i.id
--   WHERE dcl.insertion_status = 'failed'
--   ORDER BY dcl.inserted_at DESC;

-- 11) Google Calendar - Events grouped by month:
--   SELECT 
--     date_trunc('month', e.start_datetime) AS month,
--     count(*) AS event_count,
--     array_agg(DISTINCT e.summary) AS event_types
--   FROM gcalendar_event e
--   WHERE e.start_datetime >= '2024-01-01'
--     AND e.status = 'confirmed'
--   GROUP BY month
--   ORDER BY month;

-- 12) Google Calendar - Trace back from event to original diary entry:
--   SELECT 
--     e.summary AS event_title,
--     e.start_datetime,
--     i.title AS original_diary_title,
--     i.content_text AS original_content,
--     i.occurred_at AS diary_recorded_at,
--     dcl.llm_confidence,
--     dcl.llm_total_tokens,
--     dcl.llm_cost_usd
--   FROM gcalendar_event e
--   JOIN diary_calendar_link dcl ON dcl.calendar_event_id = e.event_id
--   JOIN ingest_item i ON i.id = dcl.source_diary_id
--   WHERE e.event_id = '<event_id>';

-- 13) Google Calendar - Use combined view for easy access:
--   SELECT * FROM diary_calendar_combined
--   WHERE event_tsv @@ plainto_tsquery('simple', 'dentist')
--   ORDER BY start_datetime DESC;
