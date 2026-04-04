# backend/tools/db_tools.py
from datetime import datetime
from models import db, Incident, IncidentLog, PastIncident


# ── CREATE ───────────────────────────────────────────────
def save_incident(incident_id, title, description):
    inc = Incident(
        id=incident_id,
        title=title,
        description=description,
        status="processing",
        created_at=datetime.utcnow()
    )
    db.session.add(inc)
    db.session.commit()


# ── LOG (every agent calls this) ─────────────────────────
def log_action(incident_id, agent, action, detail):
    log = IncidentLog(
        incident_id=incident_id,
        agent=agent,
        action=action,
        detail=detail,
        created_at=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()


# ── AFTER ALL AGENTS FINISH ──────────────────────────────
def agents_done(incident_id, severity,
                agent_root_cause, agent_resolution,
                agent_comms, agent_postmortem):
    inc = Incident.query.get(incident_id)
    if not inc:
        return
    inc.severity         = severity
    inc.status           = "agents_done"
    inc.agent_root_cause = agent_root_cause
    inc.agent_resolution = agent_resolution
    inc.agent_comms      = agent_comms
    inc.agent_postmortem = agent_postmortem
    db.session.commit()


# ── ASSIGN ───────────────────────────────────────────────
def assign_incident(incident_id, developer_name):
    inc = Incident.query.get(incident_id)
    if not inc:
        return
    inc.status      = "assigned"
    inc.assigned_to = developer_name
    inc.assigned_at = datetime.utcnow()
    db.session.commit()


# ── RESOLVE ──────────────────────────────────────────────
def resolve_incident(incident_id, resolved_by,
                     human_validated,
                     human_root_cause,
                     human_resolution):
    inc = Incident.query.get(incident_id)
    if not inc:
        return
    inc.status           = "resolved"
    inc.resolved_by      = resolved_by
    inc.resolved_at      = datetime.utcnow()
    inc.human_validated  = human_validated
    inc.human_root_cause = human_root_cause
    inc.human_resolution = human_resolution
    db.session.commit()

    # Graduate into past_incidents using the FK relationship
    _graduate_to_history(inc, human_validated,
                         human_root_cause, human_resolution)


def _graduate_to_history(inc, agent_was_correct,
                          human_root_cause, human_resolution):
    confidence = "human_verified" if agent_was_correct else "human_verified"
    # both cases are human_verified — agent_only is only for seeded data

    past = PastIncident(
        incident_id        = inc.id,          # FK to incidents table
        title              = inc.title,
        description        = inc.description,
        severity           = inc.severity,
        agent_root_cause   = inc.agent_root_cause,
        agent_resolution   = inc.agent_resolution,
        human_root_cause   = human_root_cause or inc.agent_root_cause,
        human_resolution   = human_resolution,
        agent_was_correct  = agent_was_correct,
        resolution_confidence = confidence,
        created_at         = datetime.utcnow()
    )
    db.session.add(past)
    db.session.commit()


# ── READ ─────────────────────────────────────────────────
def get_incident(incident_id):
    inc = Incident.query.get(incident_id)
    return inc.to_dict() if inc else None

def get_logs(incident_id):
    logs = IncidentLog.query \
        .filter_by(incident_id=incident_id) \
        .order_by(IncidentLog.created_at) \
        .all()
    return [l.to_dict() for l in logs]

def list_incidents():
    incs = Incident.query \
        .order_by(Incident.created_at.desc()) \
        .limit(30).all()
    return [i.to_dict() for i in incs]

def get_past_incidents_all():
    rows = PastIncident.query \
        .order_by(PastIncident.created_at.desc()).all()
    return [r.to_dict() for r in rows]