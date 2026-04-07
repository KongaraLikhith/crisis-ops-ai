import os
import logging
from typing import List

from pydantic import BaseModel
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from tools.db_tools import log_incident_event, get_incident

model_name = os.getenv("MODEL", "gemini-3-flash-preview")
logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def normalize_severity(value: str) -> str:
    sev = (value or "").strip().upper()
    return sev if sev in SEVERITY_ORDER else "P2"


class RunbookStep(BaseModel):
    order: int
    title: str
    owner: str
    action: str
    status: str


class TimelineEntry(BaseModel):
    timestamp_hint: str
    event: str
    source: str


class IncidentDocument(BaseModel):
    incident_id: str
    incident_title: str
    severity: str
    status: str
    timeline: List[TimelineEntry]
    runbook: List[RunbookStep]
    handoff_notes: str
    summary: str


def build_incident_timeline(
    tool_context: ToolContext,
    intake_summary: str,
    triage_report: str,
    comms_summary: str,
) -> dict:
    timeline = [
        {
            "timestamp_hint": "T+00m",
            "event": f"Incident created and acknowledged. {intake_summary}",
            "source": "intake_agent",
        },
        {
            "timestamp_hint": "T+05m",
            "event": f"Triage completed. {triage_report}",
            "source": "triage_agent",
        },
        {
            "timestamp_hint": "T+10m",
            "event": f"Communications prepared. {comms_summary}",
            "source": "comms_agent",
        },
    ]

    tool_context.state["INCIDENT_TIMELINE"] = timeline
    logger.info("[Docs] build_incident_timeline: %d entries", len(timeline))
    return {"timeline": timeline}


def generate_runbook_steps(
    tool_context: ToolContext,
    confirmed_severity: str,
    blast_radius: str,
    recommended_action: str,
) -> dict:
    sev = normalize_severity(confirmed_severity)

    steps: list[dict] = [
        {
            "order": 1,
            "title": "Stabilize impact",
            "owner": "incident_commander",
            "action": "Confirm current blast radius and ensure mitigation owners are assigned.",
            "status": "pending",
        },
        {
            "order": 2,
            "title": "Validate affected systems",
            "owner": "triage_lead",
            "action": "Verify the impacted systems list against live telemetry and logs.",
            "status": "pending",
        },
        {
            "order": 3,
            "title": "Coordinate communications",
            "owner": "comms_lead",
            "action": "Send internal updates and prepare the next stakeholder update.",
            "status": "pending",
        },
    ]

    if sev == "P0":
        steps.append(
            {
                "order": 4,
                "title": "Immediate executive escalation",
                "owner": "incident_commander",
                "action": "Brief executive stakeholders, confirm command ownership, and track the next leadership checkpoint.",
                "status": "pending",
            }
        )
    elif sev == "P1":
        steps.append(
            {
                "order": 4,
                "title": "Urgent leadership escalation",
                "owner": "incident_commander",
                "action": "Brief leadership and confirm the next checkpoint for active mitigation.",
                "status": "pending",
            }
        )
    else:
        steps.append(
            {
                "order": 4,
                "title": "Standard follow-up",
                "owner": "incident_commander",
                "action": "Track mitigation progress and confirm the next update window.",
                "status": "pending",
            }
        )

    if blast_radius in ("regional", "global"):
        steps.append(
            {
                "order": len(steps) + 1,
                "title": "Cross-team coordination",
                "owner": "operations_lead",
                "action": "Coordinate remediation across all impacted teams and dependencies.",
                "status": "pending",
            }
        )

    if recommended_action in ("page_oncall", "executive_brief"):
        steps.append(
            {
                "order": len(steps) + 1,
                "title": "Track escalations",
                "owner": "scribe",
                "action": "Record all escalations, owners, and follow-up times in the incident log.",
                "status": "pending",
            }
        )

    tool_context.state["INCIDENT_RUNBOOK"] = steps
    logger.info("[Docs] generate_runbook_steps: %d steps", len(steps))
    return {"runbook": steps}


def create_handoff_notes(
    tool_context: ToolContext,
    incident_id: str,
    incident_title: str,
    triage_report: str,
    comms_summary: str,
) -> dict:
    notes = (
        f"Incident {incident_id} ({incident_title}) remains active. "
        f"Latest triage: {triage_report} "
        f"Latest communications status: {comms_summary} "
        f"Next operator should verify mitigation progress, confirm the next update window, "
        f"and continue documenting all decisions."
    )

    tool_context.state["HANDOFF_NOTES"] = notes
    logger.info("[Docs] create_handoff_notes: incident=%s", incident_id)
    return {"handoff_notes": notes}


def save_incident_document(
    tool_context: ToolContext,
    summary: str,
) -> dict:
    document = IncidentDocument(
        incident_id=tool_context.state.get("INCIDENT_ID", "unknown"),
        incident_title=tool_context.state.get("INCIDENT_TITLE", "Unnamed incident"),
        severity=normalize_severity(
            tool_context.state.get(
                "CONFIRMED_SEVERITY",
                tool_context.state.get("INCIDENT_SEVERITY", "P2"),
            )
        ),
        status=tool_context.state.get("INCIDENT_STATUS", "open"),
        timeline=[
            TimelineEntry(**entry)
            for entry in tool_context.state.get("INCIDENT_TIMELINE", [])
        ],
        runbook=[
            RunbookStep(**step)
            for step in tool_context.state.get("INCIDENT_RUNBOOK", [])
        ],
        handoff_notes=tool_context.state.get("HANDOFF_NOTES", ""),
        summary=summary,
    )

    tool_context.state["INCIDENT_DOCUMENT"] = document.model_dump()
    log_incident_event(
        incident_id=document.incident_id,
        agent="Docs",
        action="incident_document_updated",
        detail="Incident document, timeline, and runbook generated.",
    )

    logger.info(
        "[Docs] save_incident_document: id=%s timeline=%d runbook=%d",
        document.incident_id, len(document.timeline), len(document.runbook),
    )
    return {"status": "success", "incident_document": document.model_dump()}


docs_agent = Agent(
    name="crisis_docs",
    model=model_name,
    description=(
        "Generates the incident timeline, operational runbook, and handoff notes. "
        "Produces a structured incident document in shared state for downstream use."
    ),
    instruction="""
You are the CrisisOps Documentation Agent.

Your role is to produce a clean operational record of the incident so the response can continue smoothly.

SEVERITY SCALE:
- P0: most severe, immediate escalation
- P1: high severity
- P2: least severe among these priorities

━━━ STEP 1 — Build the timeline ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `build_incident_timeline` with:
  - intake_summary = { intake_summary }
  - triage_report  = { triage_report }
  - comms_summary  = { comms_summary }

━━━ STEP 2 — Generate runbook steps ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `generate_runbook_steps` using values derived from { triage_report }:
  - confirmed_severity
  - blast_radius
  - recommended_action

━━━ STEP 3 — Create handoff notes ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `create_handoff_notes` with:
  - incident_id    = { INCIDENT_ID }
  - incident_title = { INCIDENT_TITLE }
  - triage_report  = { triage_report }
  - comms_summary  = { comms_summary }

━━━ STEP 4 — Save the incident document ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `save_incident_document` with a concise summary covering:
  - current severity and status
  - whether communications are active
  - what the next operator should do

━━━ STEP 5 — Present findings ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Output the report in this exact format:

## 📝 Incident Document — { INCIDENT_ID }

| Field | Value |
|-------|-------|
| Severity | |
| Status | |
| Timeline Entries | |
| Runbook Steps | |

**Summary:** <1–2 sentences>

Be structured, clear, and operationally useful.

━━━ CONTEXT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCIDENT_ID: { INCIDENT_ID }
INCIDENT_TITLE: { INCIDENT_TITLE }
INTAKE_SUMMARY: { intake_summary }
TRIAGE_REPORT: { triage_report }
COMMS_SUMMARY: { comms_summary }
""",
    tools=[
        build_incident_timeline,
        generate_runbook_steps,
        create_handoff_notes,
        save_incident_document,
        log_incident_event,
        get_incident,
    ],
    output_key="incident_document",
)
