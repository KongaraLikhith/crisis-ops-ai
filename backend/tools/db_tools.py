# backend/tools/db_tools.py
from datetime import datetime
from models import db, Incident, IncidentLog, PastIncident
from tools.search_tool import get_embedding

def log_action(incident_id, agent, action, detail=""):
    """Helper to write to the live agent activity feed."""
    log = IncidentLog(
        incident_id=incident_id,
        agent=agent,
        action=action,
        detail=detail,
        created_at=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()

def save_incident(incident_id, title, description):
    """Triggered when a new incident comes in from the UI."""
    inc = Incident(
        id=incident_id,
        title=title,
        description=description,
        status="processing"
    )
    db.session.add(inc)
    db.session.commit()
    log_action(incident_id, "System", "Incident Created", f"Title: {title}")

def agents_done(incident_id, severity, root_cause, resolution, comms, docs):
    """Triggered when the Commander and sub-agents finish their work."""
    inc = db.session.get(Incident, incident_id)
    if inc:
        inc.status = "agents_done"
        inc.severity = severity
        inc.agent_root_cause = root_cause
        inc.agent_resolution = resolution
        inc.agent_comms = comms
        inc.agent_postmortem = docs
        db.session.commit()
        log_action(incident_id, "Commander", "Agents Finished", "All AI analysis complete.")

def assign_incident(incident_id, developer_name):
    """Triggered when a human takes ownership of the ticket."""
    inc = db.session.get(Incident, incident_id)
    if inc:
        inc.status = "assigned"
        inc.assigned_to = developer_name
        inc.assigned_at = datetime.utcnow()
        db.session.commit()
        log_action(incident_id, "System", "Assigned", f"Assigned to {developer_name}")

def resolve_incident(incident_id, resolved_by, agent_was_correct, human_root_cause, human_resolution):
    """Triggered when the incident is fixed. Saves it to historical memory with embeddings."""
    inc = db.session.get(Incident, incident_id)
    if inc:
        # 1. Update the live incident status
        inc.status = "resolved"
        inc.resolved_by = resolved_by
        inc.resolved_at = datetime.utcnow()
        inc.human_validated = agent_was_correct
        inc.human_root_cause = human_root_cause
        inc.human_resolution = human_resolution
        db.session.commit()
        
        log_action(incident_id, "System", "Resolved", f"Resolved by {resolved_by}")

        # 2. Prepare the text for AI "Memory"
        # We combine the title, the cause, and the fix so the AI can find it later
        memory_text = f"Title: {inc.title}. Root Cause: {human_root_cause}. Resolution: {human_resolution}"
        
        # 3. Generate the embedding vector automatically
        print(f"--- AI Ingestion: Generating embedding for {incident_id} ---")
        vector = get_embedding(memory_text)

        # 4. Save to historical memory WITH the embedding
        past_inc = PastIncident(
            incident_id=inc.id,
            title=inc.title,
            description=inc.description,
            severity=inc.severity,
            agent_root_cause=inc.agent_root_cause,
            agent_resolution=inc.agent_resolution,
            human_root_cause=human_root_cause,
            human_resolution=human_resolution,
            agent_was_correct=agent_was_correct,
            embedding=vector,  # <--- THIS IS THE MAGIC LINE
            resolution_confidence="human_verified",
            created_at=datetime.utcnow()
        )
        db.session.add(past_inc)
        db.session.commit()
        print(f"--- AI Ingestion: {incident_id} is now searchable memory! ---")

def get_incident(incident_id):
    """Fetch a single incident for the UI."""
    inc = db.session.get(Incident, incident_id)
    return inc.to_dict() if inc else None

def list_incidents():
    """Fetch all incidents for the sidebar."""
    incidents = Incident.query.order_by(Incident.created_at.desc()).all()
    return [inc.to_dict() for inc in incidents]

def get_logs(incident_id):
    """Fetch the live timeline feed for the UI."""
    logs = IncidentLog.query.filter_by(incident_id=incident_id).order_by(IncidentLog.created_at.asc()).all()
    return [log.to_dict() for log in logs]