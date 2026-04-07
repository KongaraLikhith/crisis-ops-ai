from datetime import datetime

from models import db, Incident, IncidentLog, PastIncident
from tools.embedding_tool import embed_resolved_incident

VALID_SEVERITIES = {"P0", "P1", "P2"}
DEFAULT_SEVERITY = "P2"


def normalize_severity(value):
    sev = (value or "").strip().upper()
    return sev if sev in VALID_SEVERITIES else DEFAULT_SEVERITY


# ── CREATE ───────────────────────────────────────────────
def save_incident(incident_id, title, description):
    inc = Incident(
        id=incident_id,
        title=title,
        description=description,
        status="processing",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(inc)
    db.session.commit()


def create_incident(incident_id: str, title: str, description: str):
    """Create a new incident and return the stored row as a dict."""
    save_incident(incident_id, title, description)
    inc = db.session.get(Incident, incident_id)
    return inc.to_dict() if inc else {"incident_id": incident_id}


def update_incident_status(incident_id: str, status: str):
    """Update incident lifecycle status."""
    inc = db.session.get(Incident, incident_id)
    if not inc:
        return {"status": "not_found"}

    inc.status = status
    inc.updated_at = datetime.utcnow()
    db.session.commit()

    return {
        "status": "updated",
        "incident_id": incident_id,
        "new_status": status,
    }


def log_incident_event(
    incident_id: str,
    event_type: str = None,
    detail: str = "",
    agent: str = None,
    action: str = None,
):
    """
    Log an incident event.

    Preferred usage:
        log_incident_event(
            incident_id="INC-123",
            agent="triage_agent",
            action="triage_completed",
            detail="Severity=P0, blast_radius=global",
        )

    Backward-compatible usage:
        log_incident_event(
            incident_id="INC-123",
            event_type="triage_completed",
            detail="Severity=P0, blast_radius=global",
        )

    If agent/action are not provided, event_type is used for both to avoid
    breaking older agent code while callers are migrated.
    """
    final_agent = agent or event_type or "system"
    final_action = action or event_type or "event_logged"

    log_action(
        incident_id,
        agent=final_agent,
        action=final_action,
        detail=detail,
    )

    return {
        "status": "logged",
        "incident_id": incident_id,
        "agent": final_agent,
        "event_type": final_action,
    }


def list_open_incidents():
    """List unresolved incidents."""
    incs = (
        Incident.query.filter(Incident.status != "resolved")
        .order_by(Incident.created_at.desc())
        .limit(50)
        .all()
    )
    return [i.to_dict() for i in incs]


# ── LOG ──────────────────────────────────────────────────
def log_action(incident_id, agent, action, detail):
    """Low-level incident log writer."""
    log = IncidentLog(
        incident_id=incident_id,
        agent=agent,
        action=action,
        detail=detail,
        created_at=datetime.utcnow(),
    )
    db.session.add(log)
    db.session.commit()


# ── AFTER ALL AGENTS FINISH ──────────────────────────────
def agents_done(
    incident_id,
    severity,
    agent_root_cause,
    agent_resolution,
    agent_comms,
    agent_postmortem,
    category=None,
):
    """
    Persist final agent outputs back to Incident and PastIncident.
    """
    inc = db.session.get(Incident, incident_id)
    if not inc:
        return

    severity = normalize_severity(severity)
    category = normalize_severity(category) if category else severity

    inc.severity = severity
    inc.status = "agents_done"
    inc.updated_at = datetime.utcnow()

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
            updated_at=datetime.utcnow(),
        )
        db.session.add(past)
    else:
        past.title = inc.title
        past.description = inc.description
        past.severity = severity
        past.category = category
        past.agent_root_cause = agent_root_cause
        past.agent_resolution = agent_resolution
        past.agent_comms = agent_comms
        past.agent_postmortem = agent_postmortem
        past.updated_at = datetime.utcnow()

    db.session.commit()


# ── ASSIGN ───────────────────────────────────────────────
def assign_incident(incident_id, developer_name):
    """Assign an incident to a developer."""
    inc = db.session.get(Incident, incident_id)
    if not inc:
        return

    inc.status = "assigned"
    inc.assigned_to = developer_name
    inc.assigned_at = datetime.utcnow()
    inc.updated_at = datetime.utcnow()
    db.session.commit()


# ── RESOLVE ──────────────────────────────────────────────
def resolve_incident(
    incident_id,
    resolved_by,
    agent_was_correct,
    human_root_cause,
    human_resolution,
):
    """
    Resolve an incident and promote/update its history row.
    """
    inc = db.session.get(Incident, incident_id)
    if not inc:
        return

    inc.status = "resolved"
    inc.resolved_by = resolved_by
    inc.resolved_at = datetime.utcnow()
    inc.updated_at = datetime.utcnow()
    db.session.commit()

    past_incident = _graduate_to_history(
        inc,
        agent_was_correct,
        human_root_cause,
        human_resolution,
    )
    embed_resolved_incident(past_incident)


def _graduate_to_history(inc, agent_was_correct, human_root_cause, human_resolution):
    """
    Create or update the historical incident record after resolution.
    """
    past = PastIncident.query.filter_by(incident_id=inc.id).first()

    if not past:
        past = PastIncident(
            incident_id=inc.id,
            title=inc.title,
            description=inc.description,
            severity=normalize_severity(inc.severity),
            category=normalize_severity(inc.severity),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
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
    """Fetch a single incident as a dict."""
    inc = db.session.get(Incident, incident_id)
    return inc.to_dict() if inc else None


def get_logs(incident_id):
    """Fetch incident logs oldest-first."""
    logs = (
        IncidentLog.query.filter_by(incident_id=incident_id)
        .order_by(IncidentLog.created_at)
        .all()
    )
    return [l.to_dict() for l in logs]


def list_incidents():
    """Fetch recent incidents."""
    incs = Incident.query.order_by(Incident.created_at.desc()).limit(30).all()
    return [i.to_dict() for i in incs]


def get_past_incidents_all():
    """Fetch all historical incidents."""
    rows = PastIncident.query.order_by(PastIncident.created_at.desc()).all()
    return [r.to_dict() for r in rows]


def get_past_incident_from_db(incident_id):
    """Fetch historical records for a specific incident ID."""
    rows = (
        PastIncident.query.filter_by(incident_id=incident_id)
        .order_by(PastIncident.created_at.desc())
        .all()
    )
    return [r.to_dict() for r in rows]
