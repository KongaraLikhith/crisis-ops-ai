from database import run_query
from datetime import datetime

# ── CREATE ──────────────────────────────────────────────
def save_incident(incident_id, title, description):
    run_query(
        """INSERT INTO incidents
           (id, title, description, status)
           VALUES (%s, %s, %s, 'processing')""",
        (incident_id, title, description)
    )

# ── LOGGING (called by every agent) ─────────────────────
def log_action(incident_id, agent, action, detail):
    run_query(
        """INSERT INTO incident_logs
           (incident_id, agent, action, detail)
           VALUES (%s, %s, %s, %s)""",
        (incident_id, agent, action, detail)
    )

# ── AFTER ALL AGENTS FINISH (called by commander) ───────
def agents_done(incident_id, severity,
                agent_root_cause, agent_resolution,
                agent_comms, agent_postmortem):
    run_query(
        """UPDATE incidents SET
             severity          = %s,
             status            = 'agents_done',
             agent_root_cause  = %s,
             agent_resolution  = %s,
             agent_comms       = %s,
             agent_postmortem  = %s
           WHERE id = %s""",
        (severity, agent_root_cause, agent_resolution,
         agent_comms, agent_postmortem, incident_id)
    )

# ── ASSIGN TO A DEVELOPER ───────────────────────────────
def assign_incident(incident_id, developer_name):
    run_query(
        """UPDATE incidents SET
             status       = 'assigned',
             assigned_to  = %s,
             assigned_at  = NOW()
           WHERE id = %s""",
        (developer_name, incident_id)
    )

# ── RESOLVE (human fills this in) ───────────────────────
def resolve_incident(incident_id, resolved_by,
                     human_validated,        # True/False
                     human_root_cause,       # None if agent was correct
                     human_resolution):      # what they actually did
    run_query(
        """UPDATE incidents SET
             status            = 'resolved',
             resolved_by       = %s,
             resolved_at       = NOW(),
             human_validated   = %s,
             human_root_cause  = %s,
             human_resolution  = %s
           WHERE id = %s""",
        (resolved_by, human_validated,
         human_root_cause, human_resolution, incident_id)
    )
    # Auto-graduate into past_incidents so future Triage can learn
    _graduate_to_history(incident_id, human_validated,
                         human_root_cause, human_resolution)

def _graduate_to_history(incident_id, agent_was_correct,
                          human_root_cause, human_resolution):
    """Copies resolved incident into past_incidents for future search."""
    rows = run_query(
        "SELECT title, description, severity, agent_root_cause, agent_resolution FROM incidents WHERE id=%s",
        (incident_id,), fetch=True
    )
    if not rows: return
    row = rows[0]
    confidence = 'human_verified' if agent_was_correct else 'human_corrected'

    run_query(
        """INSERT INTO past_incidents
           (title, description, severity,
            agent_root_cause, agent_resolution,
            human_root_cause, human_resolution,
            agent_was_correct, resolution_confidence)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (row[0], row[1], row[2],
         row[3], row[4],
         human_root_cause or row[3],   # fall back to agent if human didn't change
         human_resolution,
         agent_was_correct, confidence)
    )

# ── READ ─────────────────────────────────────────────────
def get_incident(incident_id):
    rows = run_query(
        "SELECT * FROM incidents WHERE id=%s", (incident_id,), fetch=True
    )
    if not rows: return None
    r = rows[0]
    return {
        "id": r[0], "title": r[1], "description": r[2],
        "severity": r[3], "status": r[4],
        "agent_root_cause": r[5], "agent_resolution": r[6],
        "agent_comms": r[7], "agent_postmortem": r[8],
        "assigned_to": r[9], "assigned_at": str(r[10]),
        "human_validated": r[11],
        "human_root_cause": r[12], "human_resolution": r[13],
        "resolved_by": r[14], "resolved_at": str(r[15]),
        "created_at": str(r[16])
    }

def get_logs(incident_id):
    rows = run_query(
        """SELECT agent, action, detail, created_at
           FROM incident_logs WHERE incident_id=%s
           ORDER BY created_at""",
        (incident_id,), fetch=True
    )
    return [{"agent":r[0],"action":r[1],
             "detail":r[2],"time":str(r[3])} for r in rows]

def list_incidents():
    rows = run_query(
        """SELECT id, title, severity, status,
                  assigned_to, created_at
           FROM incidents ORDER BY created_at DESC LIMIT 30""",
        fetch=True
    )
    return [{"id":r[0],"title":r[1],"severity":r[2],
             "status":r[3],"assigned_to":r[4],"time":str(r[5])}
            for r in rows]