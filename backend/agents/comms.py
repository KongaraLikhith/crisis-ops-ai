import os
import logging
from typing import List, Optional

from pydantic import BaseModel
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from tools.slack_tool import send_slack_message
from tools.db_tools import log_incident_event, get_contacts_by_team
from tools.mcp_toolkit import GoogleMCPToolkit

mcp = GoogleMCPToolkit()

model_name = os.getenv("MODEL", "gemini-2.0-flash")
logger = logging.getLogger(__name__)


class StakeholderMessage(BaseModel):
    audience: str
    channel: str
    subject: str
    body: str
    priority: str


class CommsSummary(BaseModel):
    incident_id: str
    incident_title: str
    confirmed_severity: str
    internal_status: str
    customer_status: str
    next_update_eta: str
    stakeholders_contacted: List[str]
    messages: List[StakeholderMessage]
    summary: str


def classify_incident_status(
    tool_context: ToolContext,
    confirmed_severity: str,
    blast_radius: str,
    recommended_action: str,
) -> dict:
    """
    Classify the incident into communication statuses for internal and customer-facing updates.

    Persists INTERNAL_COMMS_STATUS, CUSTOMER_COMMS_STATUS, and NEXT_UPDATE_ETA.
    Returns a dict with those three values.
    """
    if confirmed_severity == "P1":
        internal_status = "major_incident"
        customer_status = "service_disruption"
        next_update_eta = "15 minutes"
    elif confirmed_severity == "P2":
        internal_status = "high_priority_incident"
        customer_status = "degraded_service"
        next_update_eta = "30 minutes"
    elif blast_radius == "regional":
        internal_status = "investigating"
        customer_status = "partial_impact"
        next_update_eta = "30 minutes"
    elif recommended_action == "monitor":
        internal_status = "monitoring"
        customer_status = "no_external_update_needed"
        next_update_eta = "60 minutes"
    else:
        internal_status = "investigating"
        customer_status = "investigating"
        next_update_eta = "30 minutes"

    tool_context.state["INTERNAL_COMMS_STATUS"] = internal_status
    tool_context.state["CUSTOMER_COMMS_STATUS"] = customer_status
    tool_context.state["NEXT_UPDATE_ETA"] = next_update_eta

    logger.info(
        "[Comms] classify_incident_status: internal=%s customer=%s eta=%s",
        internal_status, customer_status, next_update_eta,
    )
    return {
        "internal_status": internal_status,
        "customer_status": customer_status,
        "next_update_eta": next_update_eta,
    }


def draft_stakeholder_messages(
    tool_context: ToolContext,
    incident_id: str,
    incident_title: str,
    confirmed_severity: str,
    internal_status: str,
    customer_status: str,
    next_update_eta: str,
) -> dict:
    """
    Draft communication payloads for leadership, responders, and optionally customers.

    Persists DRAFT_MESSAGES and STAKEHOLDERS_CONTACTED to state.
    Returns the structured message list.
    """
    title = incident_title.strip() or "Unnamed incident"
    sev = confirmed_severity

    internal_body = (
        f"Incident {incident_id} ({sev}) is currently {internal_status.replace('_', ' ')}. "
        f"Affected service: {title}. Response is active and the next update is due in {next_update_eta}."
    )
    responder_body = (
        f"Active incident {incident_id}: {title}. Severity {sev}. "
        f"Current status: {internal_status.replace('_', ' ')}. Use incident channel and bridge for updates."
    )

    messages: list[dict] = [
        {
            "audience": "incident_responders",
            "channel": "slack",
            "subject": f"[{incident_id}] Responder update",
            "body": responder_body,
            "priority": "urgent" if sev in ("P1", "P2") else "high",
        },
        {
            "audience": "leadership",
            "channel": "slack",
            "subject": f"[{incident_id}] Leadership update",
            "body": internal_body,
            "priority": "urgent" if sev == "P1" else "high",
        },
    ]

    stakeholders = ["incident_responders", "leadership"]

    if customer_status != "no_external_update_needed":
        customer_body = (
            f"We are investigating an issue affecting {title}. "
            f"Current status: {customer_status.replace('_', ' ')}. "
            f"Our team is actively working on it. Next update in {next_update_eta}."
        )
        messages.append(
            {
                "audience": "customers",
                "channel": "status_page",
                "subject": f"Service update: {title}",
                "body": customer_body,
                "priority": "high",
            }
        )
        stakeholders.append("customers")

    tool_context.state["DRAFT_MESSAGES"] = messages
    tool_context.state["STAKEHOLDERS_CONTACTED"] = stakeholders

    logger.info("[Comms] draft_stakeholder_messages: %d messages", len(messages))
    return {"messages": messages, "stakeholders_contacted": stakeholders}


def send_internal_updates(
    tool_context: ToolContext,
    responder_message: str,
    leadership_message: str,
    channel: Optional[str] = None,
) -> dict:
    """
    Send internal updates to Slack and record the communication event.

    Persists INTERNAL_UPDATES_SENT=True.
    Returns send status.
    """
    incident_id = tool_context.state.get("INCIDENT_ID", "unknown")

    send_slack_message(channel=channel, message=responder_message)
    send_slack_message(channel=channel, message=leadership_message)
    log_incident_event(
        incident_id=incident_id,
        event_type="internal_comms_sent",
        detail=f"Internal updates sent to {channel or 'default channel'}",
    )

    tool_context.state["INTERNAL_UPDATES_SENT"] = True
    logger.info("[Comms] send_internal_updates: incident=%s channel=%s", incident_id, channel)
    return {"status": "sent", "channel": channel or "default"}


def save_comms_summary(
    tool_context: ToolContext,
    summary: str,
) -> dict:
    """
    Assemble the final CommsSummary from state and persist it.

    This must be the last comms tool called. The saved COMMS_SUMMARY key is
    consumed by the resolution agent.
    """
    report = CommsSummary(
        incident_id=tool_context.state.get("INCIDENT_ID", "unknown"),
        incident_title=tool_context.state.get("INCIDENT_TITLE", "Unnamed incident"),
        confirmed_severity=tool_context.state.get(
            "CONFIRMED_SEVERITY", tool_context.state.get("INCIDENT_SEVERITY", "P3")
        ),
        internal_status=tool_context.state.get("INTERNAL_COMMS_STATUS", "investigating"),
        customer_status=tool_context.state.get("CUSTOMER_COMMS_STATUS", "investigating"),
        next_update_eta=tool_context.state.get("NEXT_UPDATE_ETA", "30 minutes"),
        stakeholders_contacted=tool_context.state.get("STAKEHOLDERS_CONTACTED", []),
        messages=[
            StakeholderMessage(**m)
            for m in tool_context.state.get("DRAFT_MESSAGES", [])
        ],
        summary=summary,
    )

    tool_context.state["COMMS_SUMMARY"] = report.model_dump()

    logger.info(
        "[Comms] Summary saved — id=%s severity=%s stakeholders=%d",
        report.incident_id, report.confirmed_severity, len(report.stakeholders_contacted),
    )
    return {"status": "success", "comms_summary": report.model_dump()}


comms_agent = Agent(
    name="crisis_comms",
    model=model_name,
    description=(
        "Drafts and sends internal incident communications, and prepares a "
        "customer-facing update when needed. Produces a structured CommsSummary "
        "consumed by the resolution agent."
    ),
    instruction="""
You are the CrisisOps Communications Agent.

Your job is to turn the triage findings into clear, fast, appropriate communications.

━━━ STEP 1 — Classify the communication status ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `classify_incident_status` using triage data:
  - confirmed_severity = value from { triage_report }
  - blast_radius = value from { triage_report }
  - recommended_action = value from { triage_report }

━━━ STEP 2 — Draft stakeholder messages ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `draft_stakeholder_messages` with:
  - incident_id       = { INCIDENT_ID }
  - incident_title    = { INCIDENT_TITLE }
  - confirmed_severity = value from { triage_report }
  - internal_status   = from Step 1
  - customer_status   = from Step 1
  - next_update_eta   = from Step 1

━━━ STEP 3 — Send internal updates ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `send_internal_updates` with the responder and leadership messages.
Do NOT specify a channel; it will automatically use the default channel from the environment.

Do NOT send the customer/status page message with Slack. Draft it only.

━━━ STEP 4 — Send Email Alerts (P0/P1 only) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Call `get_contacts_by_team` for the impacted teams.
2. For each contact, call `send_email` with a concise incident brief if severity is P0 or P1.
3. Include "Email alerts sent" in your summary if successful.

━━━ STEP 4 — Save the communications summary ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Call `save_comms_summary` with a concise summary covering:
  - internal comms status
  - whether customers need an update
  - next update ETA

━━━ STEP 5 — Present findings ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Output the report in this exact format:

## 📣 Comms Summary — { INCIDENT_ID }

| Field | Value |
|-------|-------|
| Internal Status | |
| Customer Status | |
| Next Update ETA | |
| Stakeholders Contacted | |

**Summary:** <1–2 sentences>

Be concise, calm, and operationally clear.

━━━ CONTEXT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INCIDENT_ID: { INCIDENT_ID }
INCIDENT_TITLE: { INCIDENT_TITLE }
TRIAGE_REPORT: { triage_report }
""",
    tools=[
        classify_incident_status,
        draft_stakeholder_messages,
        send_internal_updates,
        save_comms_summary,
        send_slack_message,
        log_incident_event,
        get_contacts_by_team,
        *mcp.get_tools(),
    ],
    output_key="comms_summary",
)
