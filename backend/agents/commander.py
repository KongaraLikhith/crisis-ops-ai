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

model_name = os.getenv("MODEL", "gemini-flash-lite-latest")
logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def normalize_severity(value: str) -> str:
    sev = (value or "").strip().upper()
    return sev if sev in SEVERITY_ORDER else "P2"


def save_incident_report(tool_context: ToolContext, report: str) -> dict:
    tool_context.state["INCIDENT_REPORT"] = report
    logger.info("[Commander] Incident report saved to state.")
    return {"status": "success"}


def save_incident_to_state(
    tool_context: ToolContext,
    incident_id: str,
    title: str,
    severity: str,
    description: str,
) -> dict:
    severity = normalize_severity(severity)

    tool_context.state["INCIDENT_ID"] = incident_id
    tool_context.state["INCIDENT_TITLE"] = title
    tool_context.state["INCIDENT_SEVERITY"] = severity
    tool_context.state["INCIDENT_DESCRIPTION"] = description
    tool_context.state["INCIDENT_STATUS"] = "open"

    logger.info(
        "[Commander] Incident saved: id=%s severity=%s title=%s",
        incident_id,
        severity,
        title,
    )
    return {
        "status": "success",
        "incident_id": incident_id,
        "severity": severity,
    }


def update_incident_in_state(
    tool_context: ToolContext,
    status: str,
    resolution_notes: str = "",
) -> dict:
    tool_context.state["INCIDENT_STATUS"] = status
    if resolution_notes:
        tool_context.state["RESOLUTION_NOTES"] = resolution_notes

    logger.info(
        "[Commander] Incident %s updated -> %s",
        tool_context.state.get("INCIDENT_ID", "unknown"),
        status,
    )
    return {"status": "updated", "new_status": status}


def get_incident_context(tool_context: ToolContext) -> dict:
    return {
        "incident_id": tool_context.state.get("INCIDENT_ID"),
        "title": tool_context.state.get("INCIDENT_TITLE"),
        "severity": tool_context.state.get("INCIDENT_SEVERITY"),
        "description": tool_context.state.get("INCIDENT_DESCRIPTION"),
        "status": tool_context.state.get("INCIDENT_STATUS"),
        "slack_channel": tool_context.state.get("SLACK_CHANNEL"),
        "slack_channel_id": tool_context.state.get("SLACK_CHANNEL_ID"),
        "war_room_link": tool_context.state.get("WAR_ROOM_LINK"),
        "calendar_event_id": tool_context.state.get("CALENDAR_EVENT_ID"),
        "calendar_event_url": tool_context.state.get("CALENDAR_EVENT_URL"),
        "incident_doc_url": tool_context.state.get("INCIDENT_DOC_URL"),
        "incident_sheet_url": tool_context.state.get("INCIDENT_SHEET_URL"),
        "resolution_notes": tool_context.state.get("RESOLUTION_NOTES"),
    }


def save_coordination_context(
    tool_context: ToolContext,
    slack_channel: str = "",
    slack_channel_id: str = "",
    war_room_link: str = "",
    calendar_event_id: str = "",
    calendar_event_url: str = "",
) -> dict:
    if slack_channel:
        tool_context.state["SLACK_CHANNEL"] = slack_channel
    if slack_channel_id:
        tool_context.state["SLACK_CHANNEL_ID"] = slack_channel_id
    if war_room_link:
        tool_context.state["WAR_ROOM_LINK"] = war_room_link
    if calendar_event_id:
        tool_context.state["CALENDAR_EVENT_ID"] = calendar_event_id
    if calendar_event_url:
        tool_context.state["CALENDAR_EVENT_URL"] = calendar_event_url

    logger.info(
        "[Commander] Coordination saved: channel=%s war_room=%s",
        tool_context.state.get("SLACK_CHANNEL_ID", ""),
        tool_context.state.get("WAR_ROOM_LINK", ""),
    )
    return {"status": "success"}


intake_agent = Agent(
    name="crisis_intake",
    model=model_name,
    description=(
        "Receives a raw incident report, persists it to the database, "
        "and saves the incident context to shared state."
    ),
    instruction="""
You are the CrisisOps intake agent.

When a new incident is reported:
1. Extract title, severity, and description.
2. Call create_incident.
3. Call save_incident_to_state.
4. Return a concise acknowledgment with incident ID, title, and severity.

INCIDENT REPORT:
{INCIDENT_REPORT}
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
        "Creates the incident Slack channel, opens the war room, "
        "posts the first mobilisation update, and stores shared coordination links."
    ),
    instruction="""
You are the CrisisOps coordination agent.

Workflow:
1. Call create_slack_channel.
2. Call create_calendar_event.
3. Call save_coordination_context.
4. Call send_slack_message with incident ID, title, severity, status, and war room link.
5. Call log_incident_event with action=coordination_started.

Do not fabricate links or IDs.
""",
    tools=[
        create_slack_channel,
        create_calendar_event,
        save_coordination_context,
        send_slack_message,
        log_incident_event,
        get_incident_context,
    ],
    output_key="coordination_summary",
)

resolution_agent = Agent(
    name="crisis_resolver",
    model=model_name,
    description=(
        "Reviews triage, comms, docs, and coordination state, then decides the current "
        "incident status and posts a final operational update."
    ),
    instruction="""
You are the CrisisOps resolution agent.

Decide one status:
- resolved
- in_progress
- escalated

Workflow:
1. Call update_incident_status.
2. Call update_incident_in_state.
3. Call send_slack_message using the saved Slack channel if available.
4. Call log_incident_event with action=status_change.
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
    description="End-to-end crisis response pipeline.",
    sub_agents=[
        intake_agent,
        coordination_agent,
        triage_agent,
        docs_agent,
        comms_agent,
        resolution_agent,
    ],
)

commander = Agent(
    name="crisis_commander",
    model=model_name,
    description="Primary orchestrator for incident response and status queries.",
    instruction="""
You are the CrisisOps Commander.

If the user is reporting a new incident:
- Let the crisis workflow handle the incident end-to-end.
- After completion, summarize the final shared state.

If the user is asking about an existing incident:
- Use list_open_incidents, get_incident, and get_upcoming_events as needed.
- Do not create a new incident.

Never invent URLs or fallback links.
""",
    tools=[
        save_incident_report,
        list_open_incidents,
        get_incident,
        get_upcoming_events,
        get_incident_context,
    ],
    sub_agents=[crisis_workflow],
)

root_agent = commander