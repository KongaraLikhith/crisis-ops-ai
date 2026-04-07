import os
import logging
from google.adk import Agent
from google.adk.agents import SequentialAgent
from google.adk.tools.tool_context import ToolContext

from tools.db_tools import (
    get_incident,
    create_incident,
    update_incident_status,
    log_incident_event,
    list_open_incidents,
)
from tools.slack_tool import send_slack_message, create_slack_channel
from tools.calendar_tool import create_calendar_event, get_upcoming_events

from agents.triage import triage_agent
from agents.comms import comms_agent
from agents.docs_agent import docs_agent

model_name = os.getenv("MODEL", "gemini-3-flash-preview")
logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def save_incident_to_state(
    tool_context: ToolContext,
    incident_id: str,
    title: str,
    severity: str,
    description: str,
) -> dict:
    """
    Persist the active incident context into agent state so every
    downstream sub-agent can reference it without extra DB round-trips.

    Severity must be one of P0, P1, or P2.
      P0 → most severe  (immediate full escalation)
      P1 → high         (urgent response)
      P2 → moderate     (standard response)
    """
    severity = severity.upper().strip()
    if severity not in SEVERITY_ORDER:
        logger.warning(
            "[State] Unrecognised severity '%s' — defaulting to P2", severity
        )
        severity = "P2"

    tool_context.state["INCIDENT_ID"] = incident_id
    tool_context.state["INCIDENT_TITLE"] = title
    tool_context.state["INCIDENT_SEVERITY"] = severity
    tool_context.state["INCIDENT_DESCRIPTION"] = description
    tool_context.state["INCIDENT_STATUS"] = "open"

    logger.info(
        "[State] Incident saved — id=%s severity=%s title=%s",
        incident_id, severity, title,
    )
    return {"status": "success", "incident_id": incident_id}


def update_incident_in_state(
    tool_context: ToolContext,
    status: str,
    resolution_notes: str = "",
) -> dict:
    """
    Update the incident status and optional resolution notes in agent state.
    Call this after the incident is resolved or escalated.
    """
    tool_context.state["INCIDENT_STATUS"] = status
    if resolution_notes:
        tool_context.state["RESOLUTION_NOTES"] = resolution_notes

    logger.info(
        "[State] Incident %s status updated → %s",
        tool_context.state.get("INCIDENT_ID", "unknown"), status,
    )
    return {"status": "updated", "new_status": status}


def get_incident_context(tool_context: ToolContext) -> dict:
    """
    Return the current incident context stored in state.
    Useful for sub-agents that need a summary of the active incident.
    """
    return {
        "incident_id": tool_context.state.get("INCIDENT_ID"),
        "title": tool_context.state.get("INCIDENT_TITLE"),
        "severity": tool_context.state.get("INCIDENT_SEVERITY"),
        "description": tool_context.state.get("INCIDENT_DESCRIPTION"),
        "status": tool_context.state.get("INCIDENT_STATUS"),
    }


intake_agent = Agent(
    name="crisis_intake",
    model=model_name,
    description=(
        "Receives a raw incident report, persists it to the database, "
        "and saves the incident context to shared state."
    ),
    instruction="""
    You are the CrisisOps intake agent.

    When an incident is reported:
    1. Extract the following fields from the user message:
       - title        : short one-line summary
       - severity     : one of [P0 | P1 | P2]
                        P0 = most critical, P1 = high, P2 = moderate
       - description  : full details as provided

    2. Call `create_incident` to persist the incident in the database.
    3. Call `save_incident_to_state` so downstream agents share the context.
    4. Acknowledge receipt: confirm the incident ID, title, and severity.

    SEVERITY SCALE (P0 is highest, P2 is lowest):
    - P0: Critical — complete service outage, data loss, or security breach.
          Triggers immediate full escalation including executive notification.
    - P1: High — major degradation or partial outage affecting many users.
          Triggers urgent team response and lead notification.
    - P2: Moderate — limited impact, workaround available.
          Triggers standard response; no executive escalation.

    Be concise and professional. This is an emergency operations context.

    INCIDENT REPORT:
    { INCIDENT_REPORT }
    """,
    tools=[
        create_incident,
        save_incident_to_state,
        get_incident_context,
    ],
    output_key="intake_summary",
)


coordination_agent = Agent(
    name="crisis_coordinator",
    model=model_name,
    description=(
        "Orchestrates the parallel response: spins up a Slack channel, "
        "schedules a bridge call, and logs the mobilisation event."
    ),
    instruction="""
    You are the CrisisOps coordination agent.

    Using the active incident from state:
    1. Call `create_slack_channel` to open a dedicated incident channel
       named #inc-<INCIDENT_ID>.
    2. Call `send_slack_message` to post the incident brief in that channel.
       - For P0: prefix message with 🔴 CRITICAL and page on-call + executives.
       - For P1: prefix with 🟠 HIGH and page on-call team lead.
       - For P2: prefix with 🟡 MODERATE and notify the on-call engineer.
    3. Call `create_calendar_event` to schedule an immediate war-room bridge.
       - P0: schedule immediately (within 5 minutes).
       - P1: schedule within 15 minutes.
       - P2: schedule within 1 hour or at next available slot.
    4. Call `log_incident_event` with:
       - incident_id = { INCIDENT_ID }
       - agent = "Coordinator"
       - action = "coordination_started"
       - detail = a brief summary of channel creation and bridge scheduling

    Keep all messages factual and urgent. Include severity and incident ID.

    INCIDENT_ID:    { INCIDENT_ID }
    INCIDENT_TITLE: { INCIDENT_TITLE }
    SEVERITY:       { INCIDENT_SEVERITY }
    DESCRIPTION:    { INCIDENT_DESCRIPTION }
    """,
    tools=[
        create_slack_channel,
        send_slack_message,
        create_calendar_event,
        log_incident_event,
        get_incident_context,
    ],
    output_key="coordination_summary",
)


resolution_agent = Agent(
    name="crisis_resolver",
    model=model_name,
    description=(
        "Monitors triage and comms outputs, determines when the incident "
        "is resolved, updates the DB, and posts a closing summary."
    ),
    instruction="""
    You are the CrisisOps resolution agent.

    Review the TRIAGE_REPORT and COMMS_SUMMARY produced by the sub-agents.

    1. Decide whether the incident is:
       - resolved    → all actions completed, service restored
       - in_progress → still being worked on
       - escalated   → requires executive or vendor involvement

    2. Apply severity-aware escalation rules:
       - P0: if not resolved within 30 min, auto-escalate; require exec sign-off
             to close.
       - P1: if not resolved within 2 hours, escalate to team lead.
       - P2: standard SLA; no automatic escalation.

    3. Call `update_incident_status` to persist the new status in the DB.
    4. Call `update_incident_in_state` to update shared state.
    5. Call `send_slack_message` to post a closing / status update to the
       incident channel.
    6. Call `log_incident_event` with:
       - incident_id = { INCIDENT_ID }
       - agent = "Resolver"
       - action = "status_change"
       - detail = the new incident status and any next steps

    Be clear and definitive. Include next steps if the incident is not resolved.

    INCIDENT_ID:    { INCIDENT_ID }
    SEVERITY:       { INCIDENT_SEVERITY }
    TRIAGE_REPORT:  { triage_report }
    COMMS_SUMMARY:  { comms_summary }
    """,
    tools=[
        update_incident_status,
        update_incident_in_state,
        send_slack_message,
        log_incident_event,
        get_incident_context,
    ],
    output_key="resolution_summary",
)


crisis_workflow = SequentialAgent(
    name="crisis_workflow",
    description=(
        "End-to-end crisis response pipeline: "
        "intake → triage + comms (parallel) → docs → coordination → resolution."
    ),
    sub_agents=[
        intake_agent,
        triage_agent,
        comms_agent,
        docs_agent,
        coordination_agent,
        resolution_agent,
    ],
)


def save_incident_report(
    tool_context: ToolContext, report: str
) -> dict:
    """Store the raw user-submitted incident report in state."""
    tool_context.state["INCIDENT_REPORT"] = report
    logger.info("[Commander] Incident report received and saved to state.")
    return {"status": "success"}


commander = Agent(
    name="crisis_commander",
    model=model_name,
    description="CrisisOps Commander — primary orchestrator for incident response.",
    instruction="""
    You are the CrisisOps Commander — the primary orchestrator for all
    crisis and incident management operations.

    SEVERITY SCALE (always refer to this when classifying or discussing incidents):
      P0 → Critical  — most severe. Immediate full escalation.
      P1 → High      — urgent. Team-lead-level response.
      P2 → Moderate  — least severe of the active priorities. Standard SLA.

    You have two responsibilities:

    ── INCIDENT RESPONSE ──────────────────────────────────────────────────────
    When the user reports a NEW incident:
    1. Acknowledge the report calmly and professionally.
    2. Call `save_incident_report` to persist the raw report to state.
    3. Hand off to `crisis_workflow` to execute the full response pipeline.

    ── STATUS QUERIES ─────────────────────────────────────────────────────────
    When the user asks about EXISTING incidents:
    - Use `list_open_incidents` or `get_incident` to retrieve current data.
    - Summarise the incident status, severity (P0/P1/P2), and any open
      action items.
    - If relevant, check `get_upcoming_events` for scheduled bridge calls.

    Always maintain a calm, authoritative tone. This is a high-stakes
    operations environment — be precise, brief, and action-oriented.
    """,
    tools=[
        save_incident_report,
        list_open_incidents,
        get_incident,
        get_upcoming_events,
    ],
    sub_agents=[crisis_workflow],
)


root_agent = commander
