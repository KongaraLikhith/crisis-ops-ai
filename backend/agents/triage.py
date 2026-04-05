import os
import logging
from typing import Optional, List

from pydantic import BaseModel
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

# ── Local tool imports ─────────────────────────────────────────────────────────
from tools.db_tools import (
    get_incident,
    update_incident_status,
    log_incident_event,
)

# ── Environment ────────────────────────────────────────────────────────────────
model_name = os.getenv("MODEL", "gemini-2.0-flash")

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic schemas
# ══════════════════════════════════════════════════════════════════════════════

class AffectedSystem(BaseModel):
    name: str
    status: str                # "degraded" | "down" | "partial" | "unknown"
    impact_description: str


class TriageReport(BaseModel):
    incident_id: str
    confirmed_severity: str            # P1 | P2 | P3 | P4
    blast_radius: str                  # "localised" | "regional" | "global"
    affected_systems: List[AffectedSystem]
    estimated_users_impacted: Optional[int]
    recommended_action: str            # "monitor" | "page_oncall" | "executive_brief"
    requires_executive_notification: bool
    requires_vendor_escalation: bool
    summary: str


# ══════════════════════════════════════════════════════════════════════════════
# Severity keyword maps
# ══════════════════════════════════════════════════════════════════════════════

_P1_SIGNALS = frozenset([
    "outage", "down", "data loss", "data breach", "breach", "revenue",
    "all users", "production down", "complete failure", "database unavailable",
    "critical", "zero access", "full outage", "total failure",
])

_P2_SIGNALS = frozenset([
    "degraded", "slow", "partial outage", "intermittent", "high error rate",
    "login failing", "payment failing", "elevated latency", "increased errors",
    "majority of users", "most users",
])

_P3_SIGNALS = frozenset([
    "some users", "minor", "workaround", "occasionally", "low impact",
    "few users", "edge case", "non-critical",
])

# System keyword → (display name, default status)
_SYSTEM_MAP = {
    "api":       ("API Gateway",          "degraded"),
    "gateway":   ("API Gateway",          "degraded"),
    "database":  ("PostgreSQL Database",  "down"),
    " db ":      ("PostgreSQL Database",  "down"),
    "auth":      ("Auth Service",         "degraded"),
    "login":     ("Auth Service",         "degraded"),
    "payment":   ("Payment Service",      "degraded"),
    "billing":   ("Payment Service",      "degraded"),
    "slack":     ("Slack Integration",    "partial"),
    "calendar":  ("Calendar Integration", "partial"),
    "frontend":  ("Frontend / CDN",       "degraded"),
    "cdn":       ("Frontend / CDN",       "degraded"),
    "storage":   ("Object Storage",       "degraded"),
    "s3":        ("Object Storage",       "degraded"),
    "queue":     ("Message Queue",        "degraded"),
    "pubsub":    ("Message Queue",        "degraded"),
    "cache":     ("Cache Layer",          "degraded"),
    "redis":     ("Cache Layer",          "degraded"),
    "search":    ("Search Service",       "degraded"),
    "alloydb":   ("AlloyDB",              "down"),
    "firestore": ("Firestore",            "degraded"),
    "cloud run": ("Cloud Run",            "degraded"),
}


# ══════════════════════════════════════════════════════════════════════════════
# Triage tools  (all accept ToolContext as first arg per ADK convention)
# ══════════════════════════════════════════════════════════════════════════════

def assess_severity(
    tool_context: ToolContext,
    description: str,
    initial_severity: str,
) -> dict:
    """
    Re-evaluate incident severity from description text.

    Scoring rules:
    - P1: full outage / data-loss / revenue / breach signals
    - P2: significant degradation / major feature down
    - P3: partial / minor / workaround available
    - P4: no strong signals — retain initial_severity if P4, else fallback to P3

    Persists CONFIRMED_SEVERITY and SEVERITY_JUSTIFICATION to shared state.
    Returns: {confirmed_severity, justification}
    """
    desc = description.lower()

    if any(sig in desc for sig in _P1_SIGNALS):
        confirmed = "P1"
        justification = "P1 signals detected: outage / data-risk / revenue impact."
    elif any(sig in desc for sig in _P2_SIGNALS):
        confirmed = "P2"
        justification = "P2 signals detected: significant degradation."
    elif any(sig in desc for sig in _P3_SIGNALS):
        confirmed = "P3"
        justification = "P3 signals detected: minor or partial impact."
    else:
        # No keyword match — trust the initial severity supplied by intake
        confirmed = initial_severity if initial_severity in ("P1", "P2", "P3", "P4") else "P3"
        justification = f"No override signals; retaining initial severity {confirmed}."

    tool_context.state["CONFIRMED_SEVERITY"] = confirmed
    tool_context.state["SEVERITY_JUSTIFICATION"] = justification

    logger.info("[Triage] assess_severity: initial=%s → confirmed=%s", initial_severity, confirmed)
    return {"confirmed_severity": confirmed, "justification": justification}


def identify_affected_systems(
    tool_context: ToolContext,
    description: str,
) -> dict:
    """
    Detect impacted systems from the incident description using keyword matching.

    Persists AFFECTED_SYSTEMS (list of dicts) to shared state.
    Returns: {affected_systems: [...], count: int}
    """
    desc = description.lower()
    affected: list[dict] = []
    seen: set[str] = set()

    for keyword, (system_name, status) in _SYSTEM_MAP.items():
        if keyword in desc and system_name not in seen:
            affected.append({
                "name": system_name,
                "status": status,
                "impact_description": (
                    f"Keyword '{keyword.strip()}' matched in incident description."
                ),
            })
            seen.add(system_name)

    if not affected:
        affected.append({
            "name": "Unknown / Under Investigation",
            "status": "unknown",
            "impact_description": "No system keywords matched — manual investigation required.",
        })

    tool_context.state["AFFECTED_SYSTEMS"] = affected

    logger.info("[Triage] identify_affected_systems: %d system(s) identified", len(affected))
    return {"affected_systems": affected, "count": len(affected)}


def calculate_blast_radius(
    tool_context: ToolContext,
    confirmed_severity: str,
    affected_system_count: int,
) -> dict:
    """
    Derive blast radius, escalation flags, and recommended action from
    severity and the number of affected systems.

    Persists BLAST_RADIUS, REQUIRES_EXEC_NOTIFICATION,
    REQUIRES_VENDOR_ESCALATION, RECOMMENDED_ACTION to shared state.

    Returns: {blast_radius, requires_executive_notification,
              requires_vendor_escalation, recommended_action}
    """
    if confirmed_severity == "P1" or affected_system_count >= 3:
        blast_radius = "global"
        exec_notify = True
        vendor_escalate = (confirmed_severity == "P1")
        action = "executive_brief"
    elif confirmed_severity == "P2" or affected_system_count == 2:
        blast_radius = "regional"
        exec_notify = False
        vendor_escalate = False
        action = "page_oncall"
    else:
        blast_radius = "localised"
        exec_notify = False
        vendor_escalate = False
        action = "monitor"

    tool_context.state["BLAST_RADIUS"] = blast_radius
    tool_context.state["REQUIRES_EXEC_NOTIFICATION"] = exec_notify
    tool_context.state["REQUIRES_VENDOR_ESCALATION"] = vendor_escalate
    tool_context.state["RECOMMENDED_ACTION"] = action

    logger.info(
        "[Triage] blast_radius=%s exec=%s vendor=%s action=%s",
        blast_radius, exec_notify, vendor_escalate, action,
    )
    return {
        "blast_radius": blast_radius,
        "requires_executive_notification": exec_notify,
        "requires_vendor_escalation": vendor_escalate,
        "recommended_action": action,
    }


def escalate_to_oncall(
    tool_context: ToolContext,
    team: str,
    reason: str,
) -> dict:
    """
    Record an on-call escalation event in the database.

    Call this when recommended_action is 'page_oncall' or 'executive_brief'.

    Args:
        team:   On-call team to page — one of: platform | security | dba | executive
        reason: Plain-English reason for the escalation.

    Persists ONCALL_PAGED=True and ONCALL_TEAM to shared state.
    Returns: {status, team, incident_id}
    """
    incident_id = tool_context.state.get("INCIDENT_ID", "unknown")

    log_incident_event(
        incident_id=incident_id,
        event_type="oncall_escalation",
        detail=f"Team: {team} | Reason: {reason}",
    )

    tool_context.state["ONCALL_PAGED"] = True
    tool_context.state["ONCALL_TEAM"] = team

    logger.info(
        "[Triage] escalate_to_oncall: team=%s incident=%s", team, incident_id
    )
    return {"status": "paged", "team": team, "incident_id": incident_id}


def save_triage_report(
    tool_context: ToolContext,
    summary: str,
) -> dict:
    """
    Assemble the final TriageReport from state and persist it.

    This must be the LAST triage tool called. The saved TRIAGE_REPORT key
    is consumed by comms_agent and resolution_agent.

    Args:
        summary: One or two sentence plain-English summary of the triage findings.

    Returns: {status, triage_report}
    """
    report = TriageReport(
        incident_id=tool_context.state.get("INCIDENT_ID", "unknown"),
        confirmed_severity=tool_context.state.get("CONFIRMED_SEVERITY", "P3"),
        blast_radius=tool_context.state.get("BLAST_RADIUS", "localised"),
        affected_systems=[
            AffectedSystem(**s)
            for s in tool_context.state.get("AFFECTED_SYSTEMS", [])
        ],
        estimated_users_impacted=tool_context.state.get("ESTIMATED_USERS_IMPACTED"),
        recommended_action=tool_context.state.get("RECOMMENDED_ACTION", "monitor"),
        requires_executive_notification=tool_context.state.get(
            "REQUIRES_EXEC_NOTIFICATION", False
        ),
        requires_vendor_escalation=tool_context.state.get(
            "REQUIRES_VENDOR_ESCALATION", False
        ),
        summary=summary,
    )

    tool_context.state["TRIAGE_REPORT"] = report.model_dump()

    # Optionally reflect status in DB for severe incidents
    if report.confirmed_severity in ("P1", "P2"):
        update_incident_status(
            incident_id=report.incident_id,
            status="in_triage",
        )
        log_incident_event(
            incident_id=report.incident_id,
            event_type="triage_completed",
            detail=f"Severity={report.confirmed_severity}, blast_radius={report.blast_radius}",
        )

    logger.info(
        "[Triage] save_triage_report: id=%s severity=%s systems=%d",
        report.incident_id,
        report.confirmed_severity,
        len(report.affected_systems),
    )
    return {"status": "success", "triage_report": report.model_dump()}


# ══════════════════════════════════════════════════════════════════════════════
# Triage Agent
# ══════════════════════════════════════════════════════════════════════════════

triage_agent = Agent(
    name="crisis_triage",
    model=model_name,
    description=(
        "Analyses the incident description, confirms severity, determines blast "
        "radius, identifies affected systems, and records an initial triage report."
    ),
    instruction="""
You are the CrisisOps Triage Agent.

Your job is to quickly but carefully assess the impact of the active incident.

━━━ STEP 1 — Confirm severity ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `assess_severity` with:
  - description       = { INCIDENT_DESCRIPTION }
  - initial_severity  = { INCIDENT_SEVERITY }

━━━ STEP 2 — Identify affected systems ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `identify_affected_systems` with:
  - description       = { INCIDENT_DESCRIPTION }

━━━ STEP 3 — Calculate blast radius ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `calculate_blast_radius` using:
  - confirmed_severity    = value from STEP 1
  - affected_system_count = length of AFFECTED_SYSTEMS from STEP 2

━━━ STEP 4 — Escalate if required ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If the recommended_action is 'page_oncall' or 'executive_brief', call
`escalate_to_oncall` with:
  - team   = the most appropriate on-call team (platform | security | dba | executive)
  - reason = a short justification referencing severity and blast radius.

━━━ STEP 5 — Save the triage report ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `save_triage_report` with a 1–2 sentence plain-English summary of:
  - confirmed severity
  - blast radius
  - key affected systems
  - recommended action

Finally, present a concise triage summary back to the user.

━━━ CONTEXT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCIDENT_ID:        { INCIDENT_ID }
INCIDENT_TITLE:     { INCIDENT_TITLE }
INCIDENT_SEVERITY:  { INCIDENT_SEVERITY }
INCIDENT_DESCRIPTION:
{ INCIDENT_DESCRIPTION }
""",
    tools=[
        assess_severity,
        identify_affected_systems,
        calculate_blast_radius,
        escalate_to_oncall,
        save_triage_report,
        get_incident,
        update_incident_status,
        log_incident_event,
    ],
    output_key="triage_report",
)
