-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- =========================
-- 1) INCIDENTS (LIVE TABLE)
-- =========================
CREATE TABLE incidents (
  id              TEXT PRIMARY KEY,
  title           TEXT NOT NULL,
  description     TEXT,

  severity        TEXT,
  status          TEXT DEFAULT 'processing',
  -- processing → agents_done → assigned → resolved

  assigned_to     TEXT,
  assigned_at     TIMESTAMP,

  resolved_by     TEXT,
  resolved_at     TIMESTAMP,

  created_at      TIMESTAMP DEFAULT NOW(),
  updated_at      TIMESTAMP DEFAULT NOW(),

  CONSTRAINT chk_incidents_severity
    CHECK (severity IN ('P0', 'P1', 'P2') OR severity IS NULL),

  CONSTRAINT chk_incidents_status
    CHECK (status IN ('processing', 'agents_done', 'assigned', 'resolved'))
);

-- =========================
-- 2) INCIDENT LOGS (TIMELINE)
-- =========================
CREATE TABLE incident_logs (
  id            SERIAL PRIMARY KEY,
  incident_id   TEXT NOT NULL,
  agent         TEXT,
  action        TEXT,
  detail        TEXT,
  created_at    TIMESTAMP DEFAULT NOW(),

  CONSTRAINT fk_incident_logs_incident
    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
);

-- =========================
-- 3) PAST INCIDENTS (ANALYSIS + MEMORY + VECTOR SEARCH)
-- =========================
CREATE TABLE past_incidents (
  id                    SERIAL PRIMARY KEY,
  incident_id           TEXT UNIQUE,

  title                 TEXT,
  description           TEXT,
  severity              TEXT,
  category              TEXT,

  -- Agent output
  agent_root_cause      TEXT,
  agent_resolution      TEXT,
  agent_comms           TEXT,
  agent_postmortem      TEXT,

  -- Human final truth
  human_root_cause      TEXT,
  human_resolution      TEXT,

  -- AI evaluation
  agent_was_correct     BOOLEAN,

  -- Trust / source quality
  resolution_confidence TEXT,
  -- 'human_verified' or 'agent_only'

  -- Vector embedding for semantic search
  embedding             VECTOR(768),

  created_at            TIMESTAMP DEFAULT NOW(),
  updated_at            TIMESTAMP DEFAULT NOW(),

  CONSTRAINT fk_past_incidents_incident
    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE SET NULL,

  CONSTRAINT chk_past_incidents_severity
    CHECK (severity IN ('P0', 'P1', 'P2') OR severity IS NULL),

  CONSTRAINT chk_past_incidents_resolution_confidence
    CHECK (resolution_confidence IN ('human_verified', 'agent_only') OR resolution_confidence IS NULL)
);

-- =========================
-- INDEXES
-- =========================

-- incidents
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_created_at ON incidents(created_at DESC);
CREATE INDEX idx_incidents_assigned_to ON incidents(assigned_to);

-- incident_logs
CREATE INDEX idx_incident_logs_incident_id ON incident_logs(incident_id);
CREATE INDEX idx_incident_logs_agent ON incident_logs(agent);
CREATE INDEX idx_incident_logs_created_at ON incident_logs(created_at DESC);

-- past_incidents
CREATE INDEX idx_past_incidents_incident_id ON past_incidents(incident_id);
CREATE INDEX idx_past_incidents_category ON past_incidents(category);
CREATE INDEX idx_past_incidents_severity ON past_incidents(severity);
CREATE INDEX idx_past_incidents_resolution_confidence ON past_incidents(resolution_confidence);
CREATE INDEX idx_past_incidents_created_at ON past_incidents(created_at DESC);