import os
import logging
from typing import Optional, List

from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from tools.search_tool import search_similar_incidents
from tools.db_tools import (
    get_incident,
    update_incident_status,
    log_incident_event,
)

model_name = os.getenv("MODEL", "gemini-3-flash-preview")
logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


class AffectedSystem(BaseModel):
    name: str
    status: str
    impact_description: str


class TriageReport(BaseModel):
    incident_id: str
    confirmed_severity: str
    blast_radius: str
    affected_systems: List[AffectedSystem]
    estimated_users_impacted: Optional[int]
    recommended_action: str
    requires_executive_notification: bool
    requires_vendor_escalation: bool
    summary: str
    similar_incidents: List[dict] = Field(default_factory=list)


_P0_SIGNALS = frozenset([
    "outage", "down", "data loss", "data breach", "breach", "revenue",
    "all users", "production down", "complete failure", "database unavailable",
    "critical", "zero access", "full outage", "total failure",
])

_P1_SIGNALS = frozenset([
    "degraded", "slow", "partial outage", "intermittent", "high error rate",
    "login failing", "payment failing", "elevated latency", "increased errors",
    "majority of users", "most users",
])

_P2_SIGNALS = frozenset([
    "some users", "minor", "workaround", "occasionally", "low impact",
    "few users", "edge case", "non-critical",
])

_SYSTEM_MAP = {
    "api": ("API Gateway", "degraded"),
    "gateway": ("API Gateway", "degraded"),
    "database": ("PostgreSQL Database", "down"),
    " db ": ("PostgreSQL Database", "down"),
    "auth": ("Auth Service", "degraded"),
    "login": ("Auth Service", "degraded"),
    "payment": ("Payment Service", "degraded"),
    "billing": ("Payment Service", "degraded"),
    "slack": ("Slack Integration", "partial"),
    "calendar": ("Calendar Integration", "partial"),
    "frontend": ("Frontend / CDN", "degraded"),
    "cdn": ("Frontend / CDN", "degraded"),
    "storage": ("Object Storage", "degraded"),
    "s3": ("Object Storage", "degraded"),
    "queue": ("Message Queue", "degraded"),
    "pubsub": ("Message Queue", "degraded"),
    "cache": ("Cache Layer", "degraded"),
    "redis": ("Cache Layer", "degraded"),
    "search": ("Search Service", "degraded"),
    "alloydb": ("AlloyDB", "down"),
    "firestore": ("Firestore", "degraded"),
    "cloud run": ("Cloud Run", "degraded"),
}


def normalize_severity(value: str) -> str:
    sev = (value or "").strip().upper()
    return sev if sev in SEVERITY_ORDER else "P2"


def find_similar_incidents(tool_context: ToolContext, description: str) -> dict:
    try:
        results = search_similar_incidents(
            query_text=description,
            limit=3,
            return_mode="json",
        )
        tool_context.state["SIMILAR_INCIDENTS"] = results
        logger.info("[Triage] find_similar_incidents: %d match(es)", len(results))
        return {
            "status": "ok",
            "count": len(results),
            "similar_incidents": results,
        }
    except Exception as e:
        logger.error("[Triage] find_similar_incidents failed: %s", str(e))
        tool_context.state["SIMILAR_INCIDENTS"] = []
        return {
            "status": "error",
            "count": 0,
            "error": str(e),
            "similar_incidents": [],
        }


def assess_severity(
    tool_context: ToolContext,
    description: str,
    initial_severity: str,
) -> dict:
    desc = description.lower()

    if any(sig in desc for sig in _P0_SIGNALS):
        confirmed = "P0"
        justification = "P0 signals detected: critical outage, data-risk, or full-service impact."
    elif any(sig in desc for sig in _P1_SIGNALS):
        confirmed = "P1"
        justification = "P1 signals detected: major degradation or broad customer impact."
    elif any(sig in desc for sig in _P2_SIGNALS):
        confirmed = "P2"
        justification = "P2 signals detected: limited or moderate impact."
    else:
        confirmed = normalize_severity(initial_severity)
        justification = f"No override signals; retaining initial severity {confirmed}."

    tool_context.state["CONFIRMED_SEVERITY"] = confirmed
    tool_context.state["SEVERITY_JUSTIFICATION"] = justification

    logger.info("[Triage] assess_severity: initial=%s → confirmed=%s", initial_severity, confirmed)
    return {"confirmed_severity": confirmed, "justification": justification}


def identify_affected_systems(
    tool_context: ToolContext,
    description: str,
) -> dict:
    desc = description.lower()
    affected: list[dict] = []
    seen: set[str] = set()

    for keyword, (system_name, status) in _SYSTEM_MAP.items():
        if keyword in desc and system_name not in seen:
            affected.append({
                "name": system_name,
                "status": status,
                "impact_description": f"Keyword '{keyword.strip()}' matched in incident description.",
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
    sev = normalize_severity(confirmed_severity)

    if sev == "P0" or affected_system_count >= 3:
        blast_radius = "global"
        exec_notify = True
        vendor_escalate = True
        action = "executive_brief"
    elif sev == "P1" or affected_system_count == 2:
        blast_radius = "regional"
        exec_notify = True
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
    incident_id = tool_context.state.get("INCIDENT_ID", "unknown")

    log_incident_event(
        incident_id=incident_id,
        agent="Triage",
        action="oncall_escalation",
        detail=f"Team: {team} | Reason: {reason}",
    )

    tool_context.state["ONCALL_PAGED"] = True
    tool_context.state["ONCALL_TEAM"] = team

    logger.info("[Triage] escalate_to_oncall: team=%s incident=%s", team, incident_id)
    return {"status": "paged", "team": team, "incident_id": incident_id}


def save_triage_report(
    tool_context: ToolContext,
    summary: str,
) -> dict:
    similar_incidents = tool_context.state.get("SIMILAR_INCIDENTS", [])

    report = TriageReport(
        incident_id=tool_context.state.get("INCIDENT_ID", "unknown"),
        confirmed_severity=normalize_severity(tool_context.state.get("CONFIRMED_SEVERITY", "P2")),
        blast_radius=tool_context.state.get("BLAST_RADIUS", "localised"),
        affected_systems=[
            AffectedSystem(**s)
            for s in tool_context.state.get("AFFECTED_SYSTEMS", [])
        ],
        estimated_users_impacted=tool_context.state.get("ESTIMATED_USERS_IMPACTED"),
        recommended_action=tool_context.state.get("RECOMMENDED_ACTION", "monitor"),
        requires_executive_notification=tool_context.state.get("REQUIRES_EXEC_NOTIFICATION", False),
        requires_vendor_escalation=tool_context.state.get("REQUIRES_VENDOR_ESCALATION", False),
        summary=summary,
        similar_incidents=similar_incidents,
    )

    tool_context.state["TRIAGE_REPORT"] = report.model_dump()

    if report.confirmed_severity in ("P0", "P1"):
        update_incident_status(
            incident_id=report.incident_id,
            status="in_triage",
        )
        log_incident_event(
            incident_id=report.incident_id,
            agent="Triage",
            action="triage_completed",
            detail=f"Severity={report.confirmed_severity}, blast_radius={report.blast_radius}",
        )

    logger.info(
        "[Triage] save_triage_report: id=%s severity=%s systems=%d similar=%d",
        report.incident_id,
        report.confirmed_severity,
        len(report.affected_systems),
        len(report.similar_incidents),
    )
    return {"status": "success", "triage_report": report.model_dump()}


triage_agent = Agent(
    name="crisis_triage",
    model=model_name,
    description=(
        "Analyses the incident description, confirms severity, finds similar past "
        "incidents, determines blast radius, identifies affected systems, and "
        "records an initial triage report."
    ),
    instruction="""
You are the CrisisOps Triage Agent.

Your job is to quickly but carefully assess the impact of the active incident.

SEVERITY SCALE:
- P0: most severe
- P1: high severity
- P2: least severe among these priorities

━━━ STEP 1 — Confirm severity ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `assess_severity` with:
  - description      = { INCIDENT_DESCRIPTION }
  - initial_severity = { INCIDENT_SEVERITY }

━━━ STEP 2 — Identify affected systems ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `identify_affected_systems` with:
  - description = { INCIDENT_DESCRIPTION }

━━━ STEP 3 — Find similar past incidents ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `find_similar_incidents` with:
  - description = { INCIDENT_DESCRIPTION }

Use any similar incidents found to inform your recommended_action and summary.

━━━ STEP 4 — Calculate blast radius ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `calculate_blast_radius` using:
  - confirmed_severity    = value from STEP 1
  - affected_system_count = length of AFFECTED_SYSTEMS from STEP 2

━━━ STEP 5 — Escalate if required ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If the recommended_action is 'page_oncall' or 'executive_brief', call
`escalate_to_oncall` with:
  - team   = the most appropriate on-call team (platform | security | dba | executive)
  - reason = a short justification referencing severity and blast radius.

━━━ STEP 6 — Save the triage report ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `save_triage_report` with a 1–2 sentence plain-English summary of:
  - confirmed severity
  - blast radius
  - key affected systems
  - recommended action
  - whether similar past incidents suggest a likely root cause or fix

Finally, present a concise triage summary back to the user.

━━━ CONTEXT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCIDENT_ID:        { INCIDENT_ID }
INCIDENT_TITLE:     { INCIDENT_TITLE }
INCIDENT_SEVERITY:  { INCIDENT_SEVERITY }
INCIDENT_DESCRIPTION:
{ INCIDENT_DESCRIPTION }
""",
    tools=[
        assess_severity,
        identify_affected_systems,
        find_similar_incidents,
        calculate_blast_radius,
        escalate_to_oncall,
        save_triage_report,
        get_incident,
        update_incident_status,
        log_incident_event,
    ],
    output_key="triage_report",
)