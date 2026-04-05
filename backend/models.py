from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index, text
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

db = SQLAlchemy()

# =========================
# 1) INCIDENTS (LIVE TABLE)
# =========================
class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(db.Text, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)

    severity = db.Column(db.Text)
    status = db.Column(db.Text, nullable=False, server_default="processing")
    # processing → agents_done → assigned → resolved

    assigned_to = db.Column(db.Text)
    assigned_at = db.Column(db.DateTime)

    resolved_by = db.Column(db.Text)
    resolved_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    logs = db.relationship(
        "IncidentLog",
        backref="incident",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True
    )

    past_incident = db.relationship(
        "PastIncident",
        backref="incident",
        uselist=False,
        lazy=True
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('P0', 'P1', 'P2') OR severity IS NULL",
            name="chk_incidents_severity"
        ),
        CheckConstraint(
            "status IN ('processing', 'agents_done', 'assigned', 'resolved')",
            name="chk_incidents_status"
        ),
        Index("idx_incidents_status", "status"),
        Index("idx_incidents_severity", "severity"),
        Index("idx_incidents_created_at", db.text("created_at DESC")),
        Index("idx_incidents_assigned_to", "assigned_to"),
    )

    def __repr__(self):
        return f"<Incident {self.id} - {self.title}>"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =========================
# 2) INCIDENT LOGS (TIMELINE)
# =========================
class IncidentLog(db.Model):
    __tablename__ = "incident_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    incident_id = db.Column(
        db.Text,
        db.ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False
    )

    agent = db.Column(db.Text)
    action = db.Column(db.Text)
    detail = db.Column(db.Text)

    created_at = db.Column(db.DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_incident_logs_incident_id", "incident_id"),
        Index("idx_incident_logs_agent", "agent"),
        Index("idx_incident_logs_created_at", db.text("created_at DESC")),
    )

    def __repr__(self):
        return f"<IncidentLog {self.id} - {self.incident_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "agent": self.agent,
            "action": self.action,
            "detail": self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =========================
# 3) PAST INCIDENTS (ANALYSIS + MEMORY + VECTOR SEARCH)
# =========================
class PastIncident(db.Model):
    __tablename__ = "past_incidents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    incident_id = db.Column(
        db.Text,
        db.ForeignKey("incidents.id", ondelete="SET NULL"),
        unique=True,
        nullable=True
    )

    title = db.Column(db.Text)
    description = db.Column(db.Text)
    severity = db.Column(db.Text)
    category = db.Column(db.Text)

    # Agent output
    agent_root_cause = db.Column(db.Text)
    agent_resolution = db.Column(db.Text)
    agent_comms = db.Column(db.Text)
    agent_postmortem = db.Column(db.Text)

    # Human final truth
    human_root_cause = db.Column(db.Text)
    human_resolution = db.Column(db.Text)

    # AI evaluation
    agent_was_correct = db.Column(db.Boolean)

    # Trust / source quality
    resolution_confidence = db.Column(db.Text)
    # 'human_verified' or 'agent_only'

    # Vector embedding for semantic search
    embedding = db.Column(Vector(768))

    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "severity IN ('P0', 'P1', 'P2') OR severity IS NULL",
            name="chk_past_incidents_severity"
        ),
        CheckConstraint(
            "resolution_confidence IN ('human_verified', 'agent_only') OR resolution_confidence IS NULL",
            name="chk_past_incidents_resolution_confidence"
        ),
        Index("idx_past_incidents_incident_id", "incident_id"),
        Index("idx_past_incidents_category", "category"),
        Index("idx_past_incidents_severity", "severity"),
        Index("idx_past_incidents_resolution_confidence", "resolution_confidence"),
        Index("idx_past_incidents_created_at", db.text("created_at DESC")),
    )

    def __repr__(self):
        return f"<PastIncident {self.id} - {self.title}>"

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
            "agent_comms": self.agent_comms,
            "agent_postmortem": self.agent_postmortem,
            "human_root_cause": self.human_root_cause,
            "human_resolution": self.human_resolution,
            "agent_was_correct": self.agent_was_correct,
            "resolution_confidence": self.resolution_confidence,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }