import os
import logging
from typing import List

from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.tools.tool_context import ToolContext

from tools.slack_tool import send_slack_message
from tools.db_tools import log_incident_event, get_contacts_by_team

model_name = os.getenv("MODEL", "gemini-flash-lite-latest")
logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


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
    messages: List[StakeholderMessage] = Field(default_factory=list)
    summary: str


def _normalize_severity(value: str) -> str:
    sev = (value or "").strip().upper()
    return sev if sev in SEVERITY_ORDER else "P2"


def _fmt_link(label: str, url: str) -> str:
    url = (url or "").strip()
    return f"{label}: {url}" if url else f"{label}: not available"


def classify_incident_status(
    tool_context: ToolContext,
    confirmed_severity: str,
    blast_radius: str,
    recommended_action: str,
) -> dict:
    sev = _normalize_severity(confirmed_severity)
    radius = (blast_radius or "").strip().lower()
    action = (recommended_action or "").strip().lower()

    if sev == "P0":
        internal_status = "critical_incident"
        customer_status = "service_outage"
        next_update_eta = "15 minutes"
    elif sev == "P1":
        internal_status = "major_incident"
        customer_status = "service_disruption"
        next_update_eta = "30 minutes"
    elif sev == "P2":
        if radius in ("regional", "global"):
            internal_status = "investigating"
            customer_status = "partial_impact"
            next_update_eta = "30 minutes"
        elif action == "monitor":
            internal_status = "monitoring"
            customer_status = "no_external_update_needed"
            next_update_eta = "60 minutes"
        else:
            internal_status = "high_priority_incident"
            customer_status = "degraded_service"
            next_update_eta = "60 minutes"
    else:
        internal_status = "investigating"
        customer_status = "investigating"
        next_update_eta = "30 minutes"

    tool_context.state["INTERNAL_COMMS_STATUS"] = internal_status
    tool_context.state["CUSTOMER_COMMS_STATUS"] = customer_status
    tool_context.state["NEXT_UPDATE_ETA"] = next_update_eta
    tool_context.state["CONFIRMED_SEVERITY"] = sev

    logger.info(
        "[Comms] classify_incident_status: severity=%s internal=%s customer=%s eta=%s",
        sev,
        internal_status,
        customer_status,
        next_update_eta,
    )
    return {
        "internal_status": internal_status,
        "customer_status": customer_status,
        "next_update_eta": next_update_eta,
    }


def build_slack_update(
    incident_id: str,
    incident_title: str,
    severity: str,
    status: str,
    next_update_eta: str,
    war_room_link: str,
    doc_url: str,
    sheet_url: str,
) -> str:
    parts = [
        f"🚨 Incident update: {incident_id}",
        f"Title: {incident_title}",
        f"Severity: {severity}",
        f"Status: {status}",
        f"Next update: {next_update_eta}",
        "",
        _fmt_link("War room", war_room_link),
        _fmt_link("Incident doc", doc_url),
        _fmt_link("Timeline sheet", sheet_url),
        "",
        "Please join the war room and review the incident doc before the next update.",
    ]
    return "\n".join(parts)


def draft_stakeholder_messages(
    tool_context: ToolContext,
    incident_id: str,
    incident_title: str,
    confirmed_severity: str,
    internal_status: str,
    customer_status: str,
    next_update_eta: str,
) -> dict:
    title = (incident_title or "").strip() or "Unnamed incident"
    sev = _normalize_severity(confirmed_severity)

    war_room_link = tool_context.state.get("WAR_ROOM_LINK", "")
    doc_url = tool_context.state.get("INCIDENT_DOC_URL", "")
    sheet_url = tool_context.state.get("INCIDENT_SHEET_URL", "")

    responder_body = build_slack_update(
        incident_id=incident_id,
        incident_title=title,
        severity=sev,
        status=internal_status.replace("_", " "),
        next_update_eta=next_update_eta,
        war_room_link=war_room_link,
        doc_url=doc_url,
        sheet_url=sheet_url,
    )

    leadership_body = "\n".join(
        [
            f"Incident {incident_id} is {internal_status.replace('_', ' ')}.",
            f"Title: {title}",
            f"Severity: {sev}",
            f"Customer status: {customer_status.replace('_', ' ')}",
            f"Next update: {next_update_eta}",
            "",
            _fmt_link("War room", war_room_link),
            _fmt_link("Incident doc", doc_url),
            _fmt_link("Timeline sheet", sheet_url),
        ]
    )

    priority = "critical" if sev == "P0" else "high" if sev == "P1" else "medium"

    messages: list[dict] = [
        {
            "audience": "incident_responders",
            "channel": "slack",
            "subject": f"[{incident_id}] Responder update",
            "body": responder_body,
            "priority": priority,
        },
        {
            "audience": "leadership",
            "channel": "slack",
            "subject": f"[{incident_id}] Leadership update",
            "body": leadership_body,
            "priority": priority,
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
                "priority": "high" if sev in ("P0", "P1") else "medium",
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
) -> dict:
    incident_id = tool_context.state.get("INCIDENT_ID", "unknown")
    channel_id = (tool_context.state.get("SLACK_CHANNEL_ID", "") or "").strip()

    tool_context.state["INTERNAL_UPDATES_SENT"] = False
    tool_context.state["INTERNAL_UPDATES_ERROR"] = ""

    if not channel_id:
        logger.warning(
            "[Comms] SLACK_CHANNEL_ID missing; skipping Slack send for incident=%s",
            incident_id,
        )
        tool_context.state["INTERNAL_UPDATES_ERROR"] = "SLACK_CHANNEL_ID missing"
        return {"status": "skipped", "reason": "SLACK_CHANNEL_ID missing"}

    try:
        result_1 = send_slack_message(message=responder_message, channel=channel_id)
        result_2 = send_slack_message(message=leadership_message, channel=channel_id)

        if not result_1.get("ok") or not result_2.get("ok"):
            error = result_1.get("error") or result_2.get("error") or "unknown_slack_error"
            tool_context.state["INTERNAL_UPDATES_ERROR"] = error
            logger.warning(
                "[Comms] send_internal_updates partial failure: incident=%s error=%s",
                incident_id,
                error,
            )
            return {
                "status": "failed",
                "error": error,
                "channel_id": channel_id,
                "responder_result": result_1,
                "leadership_result": result_2,
            }

        tool_context.state["INTERNAL_UPDATES_SENT"] = True
        tool_context.state["INTERNAL_UPDATES_CHANNEL_ID"] = channel_id

        log_incident_event(
            incident_id=incident_id,
            agent="Comms",
            action="internal_comms_sent",
            detail=f"Internal updates sent to Slack channel {channel_id}",
        )

        logger.info(
            "[Comms] send_internal_updates: incident=%s channel=%s",
            incident_id,
            channel_id,
        )
        return {
            "status": "sent",
            "channel_id": channel_id,
            "responder_result": result_1,
            "leadership_result": result_2,
        }
    except Exception as e:
        tool_context.state["INTERNAL_UPDATES_ERROR"] = str(e)
        logger.warning(
            "[Comms] send_internal_updates failed: incident=%s error=%s",
            incident_id,
            str(e),
        )
        return {"status": "failed", "error": str(e), "channel_id": channel_id}


def save_comms_summary(
    tool_context: ToolContext,
    summary: str,
) -> dict:
    report = CommsSummary(
        incident_id=tool_context.state.get("INCIDENT_ID", "unknown"),
        incident_title=tool_context.state.get("INCIDENT_TITLE", "Unnamed incident"),
        confirmed_severity=_normalize_severity(
            tool_context.state.get(
                "CONFIRMED_SEVERITY",
                tool_context.state.get("INCIDENT_SEVERITY", "P2"),
            )
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
        report.incident_id,
        report.confirmed_severity,
        len(report.stakeholders_contacted),
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

STEP 1 — Classify the communication status
Call `classify_incident_status` using triage data:
- confirmed_severity = value from triage report
- blast_radius = value from triage report
- recommended_action = value from triage report

STEP 2 — Draft stakeholder messages
Call `draft_stakeholder_messages` with:
- incident_id = INCIDENT_ID
- incident_title = INCIDENT_TITLE
- confirmed_severity = value from triage report
- internal_status = from Step 1
- customer_status = from Step 1
- next_update_eta = from Step 1

The drafted Slack messages must include:
- war room link
- incident doc link
- timeline sheet link

STEP 3 — Send internal updates
Call `send_internal_updates` with the responder and leadership messages.
Use the incident Slack channel ID stored in shared state.
Do not invent or fall back to a default channel.

STEP 4 — Save the communications summary
Call `save_comms_summary` with a concise summary covering:
- internal comms status
- whether customers need an update
- next update ETA
- whether war room/doc links were included in Slack

STEP 5 — Present findings
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
""",
    tools=[
        classify_incident_status,
        draft_stakeholder_messages,
        send_internal_updates,
        save_comms_summary,
        send_slack_message,
        log_incident_event,
        get_contacts_by_team,
    ],
    output_key="comms_summary",
)