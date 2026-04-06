# backend/agents/comms.py
# ── Communication Agent ──────────────────────────────────────────────
# Handles all external communications when an incident is triggered:
#   1. Generates a Slack message and emails via LLM
#   2. Posts to Slack (rich formatted message)
#   3. Sends email alert via Gmail MCP
#   4. Creates Google Calendar war room (P0 only)
# ─────────────────────────────────────────────────────────────────────
from agents.base import get_llm
from tools.db_tools import log_action
from tools.slack_tool import post_rich_slack_message
from tools.gmail_tool import send_incident_alert
from tools.calendar_tool import create_war_room


async def run_comms(incident_id, title, severity):
    llm = get_llm()

    # ── 1. Generate the communication message via LLM ────────
    prompt = f"""You are a communications specialist for incident response.

Incident: {title}
Severity: {severity}
Incident ID: {incident_id}

Write a concise incident alert message for the engineering team.
Include:
- Severity emoji (🔴 P0, 🟡 P1, 🟢 P2)
- What's happening
- Current status
- Incident ID for tracking

Keep it under 200 words. Be clear and professional."""

    result = llm.invoke(prompt)
    comms_message = result.content.strip()
    log_action(incident_id, "Comms", "Message drafted", comms_message[:150])

    # ── 2. Post to Slack ─────────────────────────────────────
    slack_result = post_rich_slack_message(
        incident_id=incident_id,
        title=title,
        severity=severity,
        triage_summary=comms_message
    )
    log_action(incident_id, "Comms", "Slack alert sent", slack_result)

    # ── 3. Send email via Gmail MCP ──────────────────────────
    email_result = send_incident_alert(
        incident_id=incident_id,
        title=title,
        severity=severity,
        summary=comms_message
    )
    log_action(incident_id, "Comms", "Email alert sent",
               email_result.get("result", "unknown"))

    # ── 4. Create war room for P0 ────────────────────────────
    war_room_result = ""
    if severity == "P0":
        war_room_result = create_war_room(
            incident_id=incident_id,
            title=title,
            severity=severity
        )
        log_action(incident_id, "Comms", "War room created", war_room_result)

    # ── Build combined output ────────────────────────────────
    output = comms_message
    if war_room_result:
        output += f"\n\nWar Room: {war_room_result}"

    return output
