from datetime import datetime

from sqlalchemy.orm import joinedload

from models import db, Incident, IncidentLog, PastIncident
from tools.embedding_tool import embed_text, embed_resolved_incident
from sqlalchemy.orm import joinedload
from tools.embedding_tool import embed_resolved_incident

VALID_SEVERITIES = {"P0", "P1", "P2"}
DEFAULT_SEVERITY = "P2"


def normalize_severity(value):
    sev = (value or "").strip().upper()
    return sev if sev in VALID_SEVERITIES else DEFAULT_SEVERITY


def save_incident(incident_id, title, description, severity=None):
    sev = normalize_severity(severity)
    inc = db.session.get(Incident, incident_id)

    if inc:
        inc.title = title
        inc.description = description
        inc.severity = sev
        inc.status = inc.status or "processing"
        inc.updated_at = datetime.utcnow()
    else:
        inc = Incident(
            id=incident_id,
            title=title,
            description=description,
            severity=sev,
            status="processing",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(inc)

    db.session.commit()
    return inc.to_dict()


def create_incident(incident_id: str, title: str, description: str, severity=None):
    existing = db.session.get(Incident, incident_id)
    if existing:
        return existing.to_dict()
    return save_incident(incident_id, title, description, severity=severity)


def update_incident_status(incident_id: str, status: str):
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


def log_action(incident_id, agent, action, detail):
    log = IncidentLog(
        incident_id=incident_id,
        agent=agent,
        action=action,
        detail=detail,
        created_at=datetime.utcnow(),
    )
    db.session.add(log)
    db.session.commit()
    return log.to_dict()


def log_incident_event(
    incident_id: str,
    event_type: str = None,
    detail: str = "",
    agent: str = None,
    action: str = None,
):
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
    incs = (
        Incident.query
        .options(joinedload(Incident.past_incident))
        .filter(Incident.status != "resolved")
        .order_by(Incident.created_at.desc())
        .limit(50)
        .all()
    )
    return [i.to_dict() for i in incs]


def agents_done(
    incident_id,
    severity,
    agent_root_cause,
    agent_resolution,
    agent_comms,
    agent_postmortem,
    category=None,
):
    inc = db.session.get(Incident, incident_id)
    if not inc:
        return {"status": "not_found"}

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
        past.resolution_confidence = past.resolution_confidence or "agent_only"
        past.updated_at = datetime.utcnow()

    db.session.commit()

    return {
        "status": "updated",
        "incident_id": incident_id,
        "severity": severity,
        "category": category,
    }


def assign_incident(incident_id, developer_name):
    inc = db.session.get(Incident, incident_id)
    if not inc:
        return {"status": "not_found"}

    inc.status = "assigned"
    inc.assigned_to = developer_name
    inc.assigned_at = datetime.utcnow()
    inc.updated_at = datetime.utcnow()
    db.session.commit()

    return {
        "status": "assigned",
        "incident_id": incident_id,
        "assigned_to": developer_name,
    }


def _graduate_to_history(inc, agent_was_correct, human_root_cause, human_resolution):
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


def resolve_incident(
    incident_id,
    resolved_by,
    agent_was_correct,
    human_root_cause,
    human_resolution,
):
    inc = db.session.get(Incident, incident_id)
    if not inc:
        return {"status": "not_found"}

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

    return {"status": "resolved", "incident_id": incident_id}


def get_incident(incident_id):
    inc = (
        Incident.query
        .options(joinedload(Incident.past_incident))
        .filter_by(id=incident_id)
        .first()
    )
    return inc.to_dict() if inc else None


def get_logs(incident_id):
    logs = (
        IncidentLog.query.filter_by(incident_id=incident_id)
        .order_by(IncidentLog.created_at)
        .all()
    )
    return [l.to_dict() for l in logs]


def list_incidents():
    incs = (
        Incident.query
        .options(joinedload(Incident.past_incident))
        .order_by(Incident.created_at.desc())
        .limit(30)
        .all()
    )
    return [i.to_dict() for i in incs]


def get_similarity_response(incident_id):
    """
    Find past incidents similar to the current live incident.
    1. Fetch current incident details.
    2. Embed title + description.
    3. Search PastIncident via pgvector.
    """
    inc = Incident.query.get(incident_id)
    if not inc:
        return []

    text = f"{inc.title} {inc.description or ''}"
    embedding = embed_text(text)
    
    if not embedding:
        return []
        
    return get_similar_incidents(embedding, limit=3)


def get_past_incidents_all():
    rows = PastIncident.query.order_by(PastIncident.created_at.desc()).all()
    return [r.to_dict() for r in rows]


def get_past_incident_from_db(incident_id):
    rows = (
        PastIncident.query.filter_by(incident_id=incident_id)
        .order_by(PastIncident.created_at.desc())
        .all()
    )
    return [r.to_dict() for r in rows]


def get_similar_incidents(embedding: list[float], limit: int = 3):
    if not embedding:
        return []

    try:
        results = (
            PastIncident.query
            .order_by(PastIncident.embedding.cosine_distance(embedding))
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in results]
    except Exception:
        return []


def get_runbook_by_type(incident_type: str):
    from models import Runbook
    rb = Runbook.query.filter_by(incident_type=incident_type).first()
    return rb.to_dict() if rb else None


def get_contacts_by_team(team: str):
    from models import Contact
    contacts = Contact.query.filter_by(team=team).all()
    return [c.to_dict() for c in contacts]


def log_timeline_event(incident_id: str, actor: str, action: str, detail: str):
    return log_action(incident_id, agent=actor, action=action, detail=detail)