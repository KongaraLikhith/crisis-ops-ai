# backend/tools/slack_tool.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

VALID_SEVERITIES = {"P0", "P1", "P2"}
DEFAULT_SEVERITY = "P2"


def normalize_severity(value: str) -> str:
    sev = (value or "").strip().upper()
    return sev if sev in VALID_SEVERITIES else DEFAULT_SEVERITY


def _post_slack(payload: dict) -> dict:
    """
    Internal helper for Slack API calls.
    Returns parsed JSON if successful, or a synthetic error dict.
    """
    token = SLACK_BOT_TOKEN

    if not token:
        return {"ok": False, "error": "missing_slack_token"}

    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        return response.json()

    except requests.exceptions.Timeout:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def post_to_slack(message: str, channel: str = None) -> str:
    """
    Posts a plain text message to Slack.
    Returns a status string so agents don't crash if Slack fails.
    """
    channel = channel or SLACK_CHANNEL_ID

    if not SLACK_BOT_TOKEN or not channel:
        print("[Slack] Not configured — skipping. Set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID in .env")
        return "Slack not configured"

    result = _post_slack({
        "channel": channel,
        "text": message,
    })

    if result.get("ok"):
        print(f"[Slack] Message sent to {channel}")
        return "Slack message sent"

    error = result.get("error", "unknown error")
    print(f"[Slack] API error: {error}")
    return f"Slack error: {error}"


def post_rich_slack_message(
    incident_id: str,
    title: str,
    severity: str,
    triage_summary: str,
    channel: str = None,
) -> str:
    """
    Posts a formatted Slack message with attachment styling.

    Severity model:
    - P0 = highest severity (red)
    - P1 = high severity (yellow/orange)
    - P2 = lowest of the active priorities (green)

    Adds a war room link only for P0.
    """
    channel = channel or SLACK_CHANNEL_ID
    severity = normalize_severity(severity)

    if not SLACK_BOT_TOKEN or not channel:
        return "Slack not configured"

    color_map = {
        "P0": "#e53e3e",
        "P1": "#EF9F27",
        "P2": "#1D9E75",
    }
    emoji_map = {
        "P0": "🔴",
        "P1": "🟠",
        "P2": "🟢",
    }

    color = color_map.get(severity, "#888888")
    emoji = emoji_map.get(severity, "⚪")

    war_room = ""
    if severity == "P0":
        war_room = f"\n*War room:* meet.google.com/crisis-{incident_id.lower()}"

    payload = {
        "channel": channel,
        "text": f"{emoji} [{severity}] {title}",
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} [{severity}] {title}",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Incident ID:*\n{incident_id}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Severity:*\n{severity}",
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Agent assessment:*\n{triage_summary}{war_room}",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "Sent by *CrisisOps AI* · Assign and resolve in dashboard",
                            }
                        ],
                    },
                ],
            }
        ],
    }

    result = _post_slack(payload)

    if result.get("ok"):
        print(f"[Slack] Rich message sent to {channel}")
        return "Rich Slack message sent"

    error = result.get("error", "unknown error")
    print(f"[Slack] Rich message failed ({error}), trying plain text fallback")
    return post_to_slack(
        f"{emoji} [{severity}] {title}\n{triage_summary}",
        channel=channel,
    )


def send_slack_message(message: str, channel: str | None = None) -> str:
    """Adapter used by agents – forwards to post_to_slack."""
    return post_to_slack(message=message, channel=channel)


def create_slack_channel(name: str) -> str:
    """
    Placeholder for now.
    Real implementation would call Slack conversations.create and invite the bot.
    """
    return f"#{name.lstrip('#')}"
