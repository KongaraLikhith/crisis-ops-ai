import os
import logging
import inspect
from typing import List

from pydantic import BaseModel
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from tools.db_tools import log_incident_event, get_incident
from tools.mcp_toolkit import GoogleMCPToolkit

mcp = GoogleMCPToolkit()
model_name = os.getenv("MODEL", "gemini-flash-lite-latest")
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


def render_incident_document(document: IncidentDocument) -> str:
    timeline_text = "\n".join(
        f"{i + 1}. {t.timestamp_hint} | {t.source} | {t.event}"
        for i, t in enumerate(document.timeline)
    ) or "No timeline entries."

    runbook_text = "\n".join(
        f"{s.order}. {s.title} | Owner: {s.owner} | Action: {s.action} | Status: {s.status}"
        for s in document.runbook
    ) or "No runbook steps."

    return (
        f"Incident Report: {document.incident_id}\n\n"
        f"Title: {document.incident_title}\n"
        f"Severity: {document.severity}\n"
        f"Status: {document.status}\n\n"
        f"Summary\n{document.summary}\n\n"
        f"Timeline\n{timeline_text}\n\n"
        f"Runbook\n{runbook_text}\n\n"
        f"Handoff Notes\n{document.handoff_notes}\n"
    )


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
    blast = (blast_radius or "").strip().lower()
    action = (recommended_action or "").strip().lower()

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

    if blast in ("regional", "global"):
        steps.append(
            {
                "order": len(steps) + 1,
                "title": "Cross-team coordination",
                "owner": "operations_lead",
                "action": "Coordinate remediation across all impacted teams and dependencies.",
                "status": "pending",
            }
        )

    if action in ("page_oncall", "executive_brief"):
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
        f"Latest triage: {triage_report}. "
        f"Latest communications status: {comms_summary}. "
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
        document.incident_id,
        len(document.timeline),
        len(document.runbook),
    )
    return {"status": "success", "incident_document": document.model_dump()}


def create_workspace_docs(tool_context: ToolContext) -> dict:
    document = IncidentDocument(**tool_context.state["INCIDENT_DOCUMENT"])
    doc_text = render_incident_document(document)

    tool_context.state["INCIDENT_DOCUMENT_TEXT"] = doc_text

    doc_result = mcp.create_doc(
        title=f"Incident Report: {document.incident_id}",
        content=doc_text,
    )
    if inspect.isawaitable(doc_result):
        raise TypeError("mcp.create_doc returned a coroutine; GoogleMCPToolkit.create_doc must be synchronous.")
    doc_url = doc_result.get("url", "")
    doc_id = doc_result.get("document_id", "") or doc_result.get("doc_id", "")

    sheet_result = mcp.create_sheet(
        title=f"Incident Timeline: {document.incident_id}",
        headers=["Timestamp", "Actor", "Action", "Detail"],
    )
    if inspect.isawaitable(sheet_result):
        raise TypeError("mcp.create_sheet returned a coroutine; GoogleMCPToolkit.create_sheet must be synchronous.")
    sheet_url = sheet_result.get("url", "")
    sheet_id = sheet_result.get("sheet_id", "")

    tool_context.state["INCIDENT_DOC_URL"] = doc_url
    tool_context.state["INCIDENT_DOC_ID"] = doc_id
    tool_context.state["INCIDENT_SHEET_URL"] = sheet_url
    tool_context.state["INCIDENT_SHEET_ID"] = sheet_id

    logger.info("[Docs] Workspace docs created: doc=%s sheet=%s", doc_url, sheet_url)
    return {
        "doc_url": doc_url,
        "sheet_url": sheet_url,
        "status": "success",
    }


docs_agent = Agent(
    name="crisis_docs",
    model=model_name,
    description=(
        "Generates the incident timeline, operational runbook, handoff notes, "
        "and creates the final Google Doc and Sheet."
    ),
    instruction="""
You are the CrisisOps Documentation Agent.

Your job is to create a complete incident record and write it into Google Docs.

Workflow:
1. Call build_incident_timeline.
2. Call generate_runbook_steps.
3. Call create_handoff_notes.
4. Call save_incident_document with a concise but complete summary.
5. Call create_workspace_docs to create the Google Doc and Sheet and insert the document text.

Rules:
- The Google Doc must contain the rendered incident document text.
- The document text must include title, severity, status, summary, timeline, runbook, and handoff notes.
- Use the state values created by the earlier tool calls.
- Return the doc URL and sheet URL in the final output.

Final output format:

## 📝 Incident Document — {INCIDENT_ID}

| Field | Value |
|-------|-------|
| Severity | |
| Status | |
| Timeline Entries | |
| Runbook Steps | |
| Doc URL | |
| Sheet URL | |

Summary: 1-2 concise sentences.
""",
    tools=[
        build_incident_timeline,
        generate_runbook_steps,
        create_handoff_notes,
        save_incident_document,
        create_workspace_docs,
        log_incident_event,
        get_incident,
        *mcp.get_tools(),
    ],
    output_key="incident_document",
)