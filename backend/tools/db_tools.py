from datetime import datetime
from models import db, Incident, IncidentLog, PastIncident
from tools.embedding_tool import embed_resolved_incident
from sqlalchemy.orm import joinedload

# ── CREATE ───────────────────────────────────────────────
def save_incident(incident_id, title, description):
    inc = Incident(
        id=incident_id,
        title=title,
        description=description,
        status="processing",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(inc)
    db.session.commit()
def create_incident(incident_id: str, title: str, description: str):
    """Alias used by commander intake agent. Checks for existence first."""
    existing = Incident.query.get(incident_id)
    if existing:
        return existing.to_dict()
    
    save_incident(incident_id, title, description)
    inc = Incident.query.get(incident_id)
    return inc.to_dict() if inc else {"incident_id": incident_id}

def update_incident_status(incident_id: str, status: str):
    inc = Incident.query.get(incident_id)
    if not inc:
        return {"status": "not_found"}
    inc.status = status
    inc.updated_at = datetime.utcnow()
    db.session.commit()
    return {"status": "updated", "incident_id": incident_id, "new_status": status}

def log_incident_event(incident_id: str, event_type: str, detail: str):
    """Alias wrapper over log_action with richer naming."""
    log_action(incident_id, agent=event_type, action=event_type, detail=detail)
    return {"status": "logged", "incident_id": incident_id, "event_type": event_type}

def list_open_incidents():
    incs = Incident.query \
        .options(joinedload(Incident.past_incident)) \
        .filter(Incident.status != "resolved") \
        .order_by(Incident.created_at.desc()) \
        .limit(50).all()
    return [i.to_dict() for i in incs]

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
                agent_comms, agent_postmortem,
                category=None):
    inc = Incident.query.get(incident_id)
    if not inc:
        return

    inc.severity = severity
    inc.status = "agents_done"
    inc.updated_at = datetime.utcnow()

    # Store agent analysis in past_incidents
    past = PastIncident.query.filter_by(incident_id=incident_id).first()

    if not past:
        past = PastIncident(
            incident_id=inc.id,
            title=inc.title,
            description=inc.description,
            severity=severity,
            category=category,
            agent_root_cause=agent_root_cause,
            agent_resolution=agent_resolution,
            agent_comms=agent_comms,
            agent_postmortem=agent_postmortem,
            resolution_confidence="agent_only",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(past)
    else:
        past.title = inc.title
        past.description = inc.description
        past.severity = severity
        past.category = category or past.category
        past.agent_root_cause = agent_root_cause
        past.agent_resolution = agent_resolution
        past.agent_comms = agent_comms
        past.agent_postmortem = agent_postmortem
        past.updated_at = datetime.utcnow()

    db.session.commit()


# ── ASSIGN ───────────────────────────────────────────────
def assign_incident(incident_id, developer_name):
    inc = Incident.query.get(incident_id)
    if not inc:
        return
    inc.status = "assigned"
    inc.assigned_to = developer_name
    inc.assigned_at = datetime.utcnow()
    inc.updated_at = datetime.utcnow()
    db.session.commit()



# ── RESOLVE ──────────────────────────────────────────────
def resolve_incident(incident_id, resolved_by,
                     agent_was_correct,
                     human_root_cause,
                     human_resolution):
    inc = Incident.query.get(incident_id)
    if not inc:
        return

    inc.status = "resolved"
    inc.resolved_by = resolved_by
    inc.resolved_at = datetime.utcnow()
    inc.updated_at = datetime.utcnow()
    db.session.commit()

    # Graduate/update into past_incidents
    past_incident = _graduate_to_history(
        inc,
        agent_was_correct,
        human_root_cause,
        human_resolution
    )
    embed_resolved_incident(past_incident)


def _graduate_to_history(inc, agent_was_correct,
                         human_root_cause, human_resolution):
    past = PastIncident.query.filter_by(incident_id=inc.id).first()

    if not past:
        past = PastIncident(
            incident_id=inc.id,
            title=inc.title,
            description=inc.description,
            severity=inc.severity,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(past)

    past.human_root_cause = human_root_cause or past.agent_root_cause
    past.human_resolution = human_resolution
    past.agent_was_correct = agent_was_correct
    past.resolution_confidence = "human_verified"
    past.updated_at = datetime.utcnow()

    db.session.commit()
    return past


# ── READ ─────────────────────────────────────────────────
def get_incident(incident_id):
    inc = Incident.query.options(joinedload(Incident.past_incident)).get(incident_id)
    return inc.to_dict() if inc else None

def get_logs(incident_id):
    logs = IncidentLog.query \
        .filter_by(incident_id=incident_id) \
        .order_by(IncidentLog.created_at) \
        .all()
    return [l.to_dict() for l in logs]

def list_incidents():
    incs = Incident.query \
        .options(joinedload(Incident.past_incident)) \
        .order_by(Incident.created_at.desc()) \
        .limit(30).all()
    return [i.to_dict() for i in incs]

def get_past_incidents_all():
    rows = PastIncident.query \
        .order_by(PastIncident.created_at.desc()).all()
    return [r.to_dict() for r in rows]

def get_past_incident_from_db(incident_id):
    rows = PastIncident.query \
        .filter_by(incident_id=incident_id) \
        .order_by(PastIncident.created_at.desc()).all()
    return [r.to_dict() for r in rows]


# ── DEV 3 MCP TOOLS ──────────────────────────────────────

def get_similar_incidents(embedding: list[float], limit: int = 3):
    """
    Perform semantic search for past incidents.
    Falls back to a safe empty list if pgvector is not available (e.g. SQLite).
    """
    if not embedding:
        return []
        
    try:
        # Cosine distance similarity search - Requires pgvector
        results = PastIncident.query \
            .order_by(PastIncident.embedding.cosine_distance(embedding)) \
            .limit(limit).all()
        return [r.to_dict() for r in results]
    except Exception as e:
        # Graceful fallback for SQLite or missing extension
        print(f"[DB] Similarity search skipped (pgvector not available): {e}")
        return []


def get_runbook_by_type(incident_type: str):
    """
    Fetch the remediation runbook for a specific incident category.
    """
    from models import Runbook
    rb = Runbook.query.filter_by(incident_type=incident_type).first()
    return rb.to_dict() if rb else None


def get_contacts_by_team(team: str):
    """
    Fetch stakeholder contact info for a specific team.
    """
    from models import Contact
    contacts = Contact.query.filter_by(team=team).all()
    return [c.to_dict() for c in contacts]


def log_timeline_event(incident_id: str, actor: str, action: str, detail: str):
    """
    Record an agent action in the timeline (alias for log_action).
    """
    return log_action(incident_id, agent=actor, action=action, detail=detail)

