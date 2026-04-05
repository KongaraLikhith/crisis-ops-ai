from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, ForeignKey, Text, Boolean, Integer, TIMESTAMP
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

db = SQLAlchemy()

# ============================================================
# INCIDENTS TABLE
# ============================================================
class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(Text, primary_key=True)  # e.g. INC-1001
    title = db.Column(Text, nullable=False)
    description = db.Column(Text, nullable=True)

    severity = db.Column(Text, nullable=True)  # P0, P1, P2
    status = db.Column(Text, nullable=False, default="processing")

    agent_root_cause = db.Column(Text, nullable=True)
    agent_resolution = db.Column(Text, nullable=True)
    agent_comms = db.Column(Text, nullable=True)
    agent_postmortem = db.Column(Text, nullable=True)

    assigned_to = db.Column(Text, nullable=True)
    assigned_at = db.Column(TIMESTAMP, nullable=True)

    human_validated = db.Column(Boolean, nullable=True)
    human_root_cause = db.Column(Text, nullable=True)
    human_resolution = db.Column(Text, nullable=True)
    resolved_by = db.Column(Text, nullable=True)
    resolved_at = db.Column(TIMESTAMP, nullable=True)

    created_at = db.Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    logs = relationship("IncidentLog", back_populates="incident", cascade="all, delete-orphan", lazy=True)
    historical_records = relationship("PastIncident", back_populates="incident", lazy=True)

    __table_args__ = (
        CheckConstraint("severity IN ('P0', 'P1', 'P2') OR severity IS NULL", name="chk_incidents_severity"),
        CheckConstraint("status IN ('processing', 'agents_done', 'assigned', 'resolved')", name="chk_incidents_status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "assigned_to": self.assigned_to,
        }

# ============================================================
# INCIDENT_LOGS TABLE
# ============================================================
class IncidentLog(db.Model):
    __tablename__ = "incident_logs"

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    incident_id = db.Column(Text, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    agent = db.Column(Text, nullable=True)
    action = db.Column(Text, nullable=True)
    detail = db.Column(Text, nullable=True)
    created_at = db.Column(TIMESTAMP, nullable=False, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="logs")

# ============================================================
# PAST_INCIDENTS TABLE (WITH VECTOR SEARCH)
# ============================================================
class PastIncident(db.Model):
    __tablename__ = "past_incidents"

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    incident_id = db.Column(Text, ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True)

    title = db.Column(Text, nullable=True)
    description = db.Column(Text, nullable=True)
    severity = db.Column(Text, nullable=True)
    category = db.Column(Text, nullable=True)

    agent_root_cause = db.Column(Text, nullable=True)
    agent_resolution = db.Column(Text, nullable=True)
    human_root_cause = db.Column(Text, nullable=True)
    human_resolution = db.Column(Text, nullable=True)

    agent_was_correct = db.Column(Boolean, nullable=True)
    resolution_confidence = db.Column(Text, nullable=True)

    # Vector column for AI Semantic Search
    embedding = db.Column(Vector(768))

    created_at = db.Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    incident = relationship("Incident", back_populates="historical_records")
    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "category": self.category,
            "agent_root_cause": self.agent_root_cause,
            "agent_resolution": self.agent_resolution,
            "human_root_cause": self.human_root_cause,
            "human_resolution": self.human_resolution,
            "agent_was_correct": self.agent_was_correct,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }