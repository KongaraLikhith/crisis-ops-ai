-- RAN ALL BELOW QUERIES IN SUPABASE ALREADY:

CREATE TABLE incidents (
  id                    TEXT PRIMARY KEY,
  title                 TEXT NOT NULL,
  description           TEXT,

  -- Set by Commander agent
  severity              TEXT,          -- P0, P1, P2

  -- Lifecycle status
  status                TEXT DEFAULT 'processing',
  -- processing → agents_done → assigned → resolved

  -- Set by agents (LLM output)
  agent_root_cause      TEXT,          -- what LLM thinks caused it
  agent_resolution      TEXT,          -- what LLM suggests to fix it
  agent_comms           TEXT,          -- Slack message that was sent
  agent_postmortem      TEXT,          -- draft post-mortem

  -- Set by human developer
  assigned_to           TEXT,          -- developer name or email
  assigned_at           TIMESTAMP,

  human_validated       BOOLEAN,       -- true = agent was right
  human_root_cause      TEXT,          -- actual root cause (if different)
  human_resolution      TEXT,          -- what they actually did to fix it
  resolved_by           TEXT,          -- who closed it
  resolved_at           TIMESTAMP,

  created_at            TIMESTAMP DEFAULT NOW()
);

-- INCIDENT_LOGS: live agent activity feed (unchanged)
CREATE TABLE incident_logs (
  id            SERIAL PRIMARY KEY,
  incident_id   TEXT,
  agent         TEXT,
  action        TEXT,
  detail        TEXT,
  created_at    TIMESTAMP DEFAULT NOW()
);

-- PAST_INCIDENTS: historical memory for Triage to search
-- Now has BOTH agent guess AND human truth
CREATE TABLE past_incidents (
  id                    SERIAL PRIMARY KEY,
  incident_id           TEXT,   -- nullable: real incident if available

  title                 TEXT,
  description           TEXT,
  severity              TEXT,
  category              TEXT,

  -- What the agent guessed
  agent_root_cause      TEXT,
  agent_resolution      TEXT,

  -- What actually happened (human verified)
  human_root_cause      TEXT,
  human_resolution      TEXT,

  -- Was agent correct?
  agent_was_correct     BOOLEAN,

  -- For search ranking
  resolution_confidence TEXT,  -- 'human_verified' or 'agent_only'

  created_at            TIMESTAMP DEFAULT NOW(),

  CONSTRAINT fk_past_incidents_incident
    FOREIGN KEY (incident_id) REFERENCES incidents(id)
);

-- ADDING FORIEGN KEY TO incident_logs & past_incidents
ALTER TABLE incident_logs
ADD CONSTRAINT fk_incident_logs_incident
FOREIGN KEY (incident_id) REFERENCES incidents(id); 

ALTER TABLE past_incidents
ADD CONSTRAINT fk_past_incidents_incident
FOREIGN KEY (incident_id) REFERENCES incidents(id);

-- ADDING INDEXING TO ALL THE TABLES
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
CREATE INDEX idx_past_incidents_category ON past_incidents(category);
CREATE INDEX idx_past_incidents_severity ON past_incidents(severity);
CREATE INDEX idx_past_incidents_resolution_confidence ON past_incidents(resolution_confidence);
CREATE INDEX idx_past_incidents_created_at ON past_incidents(created_at DESC);

