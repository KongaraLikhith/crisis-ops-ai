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
    get_runbook_by_type,
)

model_name = os.getenv("MODEL", "gemini-flash-lite-latest")
logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}

_P0_SIGNALS = frozenset([
    "outage",
    "down",
    "data loss",
    "data breach",
    "breach",
    "revenue",
    "all users",
    "production down",
    "complete failure",
    "database unavailable",
    "critical",
    "zero access",
    "full outage",
    "total failure",
])

_P1_SIGNALS = frozenset([
    "degraded",
    "slow",
    "partial outage",
    "intermittent",
    "high error rate",
    "login failing",
    "payment failing",
    "elevated latency",
    "increased errors",
    "majority of users",
    "most users",
])

_P2_SIGNALS = frozenset([
    "some users",
    "minor",
    "workaround",
    "occasionally",
    "low impact",
    "few users",
    "edge case",
    "non-critical",
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


class AffectedSystem(BaseModel):
    name: str
    status: str
    impact_description: str


class TriageReport(BaseModel):
    incident_id: str
    confirmed_severity: str
    blast_radius: str
    affected_systems: List[AffectedSystem]
    estimated_users_impacted: Optional[int] = None
    recommended_action: str
    requires_executive_notification: bool
    requires_vendor_escalation: bool
    oncall_paged: bool = False
    oncall_team: Optional[str] = None
    summary: str
    similar_incidents: List[dict] = Field(default_factory=list)
    runbook_matches: List[dict] = Field(default_factory=list)


def assess_severity(tool_context: ToolContext, description: str, initial_severity: str) -> dict:
    desc = f" {(description or '').lower()} "

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
        justification = f"No override signals detected; retaining initial severity {confirmed}."

    tool_context.state["CONFIRMED_SEVERITY"] = confirmed
    tool_context.state["SEVERITY_JUSTIFICATION"] = justification
    return {"confirmed_severity": confirmed, "justification": justification}


def identify_affected_systems(tool_context: ToolContext, description: str) -> dict:
    desc = f" {(description or '').lower()} "
    affected: list[dict] = []
    seen: set[str] = set()

    for keyword, (system_name, status) in _SYSTEM_MAP.items():
        if keyword in desc and system_name not in seen:
            affected.append(
                {
                    "name": system_name,
                    "status": status,
                    "impact_description": f"Keyword '{keyword.strip()}' matched in incident description.",
                }
            )
            seen.add(system_name)

    if not affected:
        affected.append(
            {
                "name": "Unknown / Under Investigation",
                "status": "unknown",
                "impact_description": "No system keywords matched; manual investigation required.",
            }
        )

    tool_context.state["AFFECTED_SYSTEMS"] = affected
    tool_context.state["AFFECTED_SYSTEM_COUNT"] = len(affected)
    return {"affected_systems": affected, "affected_system_count": len(affected)}


def find_similar_incidents(tool_context: ToolContext, description: str) -> dict:
    try:
        search_results = search_similar_incidents(
            query_text=description,
            limit=3,
            return_mode="json",
        ) or []
    except Exception as e:
        logger.warning("[Triage] search_similar_incidents failed: %s", str(e))
        search_results = []

    combined = []
    seen_ids = set()

    for item in search_results:
        incident_id = (
            item.get("incident_id")
            or item.get("id")
            or item.get("INCIDENT_ID")
            or ""
        )
        dedupe_key = incident_id or str(item)
        if dedupe_key in seen_ids:
            continue
        seen_ids.add(dedupe_key)
        combined.append(item)

    tool_context.state["SIMILAR_INCIDENTS"] = combined[:5]
    return {
        "status": "ok",
        "count": len(combined[:5]),
        "similar_incidents": combined[:5],
    }


def fetch_runbook_matches(tool_context: ToolContext, description: str) -> dict:
    desc = (description or "").lower()

    if "database" in desc or " db " in f" {desc} " or "alloydb" in desc:
        runbook_type = "database"
    elif "auth" in desc or "login" in desc:
        runbook_type = "auth"
    elif "payment" in desc or "billing" in desc:
        runbook_type = "payments"
    else:
        runbook_type = "generic"

    try:
        runbook = get_runbook_by_type(runbook_type) or []
    except Exception as e:
        logger.warning("[Triage] get_runbook_by_type failed: %s", str(e))
        runbook = []

    tool_context.state["RUNBOOK_TYPE"] = runbook_type
    tool_context.state["RUNBOOK_MATCHES"] = runbook
    return {
        "runbook_type": runbook_type,
        "runbook_matches": runbook,
    }


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
        blast_radius = "localized"
        exec_notify = False
        vendor_escalate = False
        action = "monitor"

    tool_context.state["BLAST_RADIUS"] = blast_radius
    tool_context.state["REQUIRES_EXEC_NOTIFICATION"] = exec_notify
    tool_context.state["REQUIRES_VENDOR_ESCALATION"] = vendor_escalate
    tool_context.state["RECOMMENDED_ACTION"] = action

    return {
        "blast_radius": blast_radius,
        "requires_executive_notification": exec_notify,
        "requires_vendor_escalation": vendor_escalate,
        "recommended_action": action,
    }


def escalate_to_oncall(tool_context: ToolContext, team: str, reason: str) -> dict:
    incident_id = tool_context.state.get("INCIDENT_ID", "unknown")

    log_incident_event(
        incident_id=incident_id,
        agent="Triage",
        action="oncall_escalation",
        detail=f"Team: {team} | Reason: {reason}",
    )

    tool_context.state["ONCALL_PAGED"] = True
    tool_context.state["ONCALL_TEAM"] = team
    return {"status": "paged", "team": team, "incident_id": incident_id}


def save_triage_report(tool_context: ToolContext, summary: str) -> dict:
    report = TriageReport(
        incident_id=tool_context.state.get("INCIDENT_ID", "unknown"),
        confirmed_severity=normalize_severity(
            tool_context.state.get(
                "CONFIRMED_SEVERITY",
                tool_context.state.get("INCIDENT_SEVERITY", "P2"),
            )
        ),
        blast_radius=tool_context.state.get("BLAST_RADIUS", "localized"),
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
        oncall_paged=tool_context.state.get("ONCALL_PAGED", False),
        oncall_team=tool_context.state.get("ONCALL_TEAM"),
        summary=summary,
        similar_incidents=tool_context.state.get("SIMILAR_INCIDENTS", []),
        runbook_matches=tool_context.state.get("RUNBOOK_MATCHES", []),
    )

    tool_context.state["TRIAGE_REPORT"] = report.model_dump()
    tool_context.state["INCIDENT_SEVERITY"] = report.confirmed_severity

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

Workflow:
1. Call assess_severity.
2. Call identify_affected_systems.
3. Call find_similar_incidents.
4. Call fetch_runbook_matches.
5. Call calculate_blast_radius.
6. If recommended_action is page_oncall or executive_brief, call escalate_to_oncall.
7. Call save_triage_report.

Final output:
Return a concise triage summary with:
- confirmed severity
- blast radius
- affected systems
- recommended action
- similar incident IDs if available
- whether escalation happened
""",
    tools=[
        assess_severity,
        identify_affected_systems,
        find_similar_incidents,
        fetch_runbook_matches,
        calculate_blast_radius,
        escalate_to_oncall,
        save_triage_report,
        get_incident,
        update_incident_status,
        log_incident_event,
    ],
    output_key="triage_report",
)