# backend/tools/slack_tool.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")


def post_to_slack(message: str, channel: str = None) -> str:
    """
    Posts a plain text message to Slack.
    Called by the Comms agent.
    Returns a status string (not raises) so agents don't crash if Slack fails.
    """
    token   = SLACK_BOT_TOKEN
    channel = channel or SLACK_CHANNEL_ID

    if not token or not channel:
        print("[Slack] Not configured — skipping. Set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID in .env")
        return "Slack not configured"

    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "channel": channel,
                "text": message,
            },
            timeout=10
        )
        result = response.json()

        if result.get("ok"):
            print(f"[Slack] Message sent to {channel}")
            return "Slack message sent"
        else:
            error = result.get("error", "unknown error")
            print(f"[Slack] API error: {error}")
            return f"Slack error: {error}"

    except requests.exceptions.Timeout:
        print("[Slack] Request timed out")
        return "Slack timeout"
    except Exception as e:
        print(f"[Slack] Unexpected error: {e}")
        return f"Slack failed: {str(e)}"


def post_rich_slack_message(incident_id: str, title: str,
                             severity: str, triage_summary: str) -> str:
    """
    Posts a formatted Slack message with colored sidebar (attachment format).
    P0 = red, P1 = yellow, P2 = green.
    Called by Comms agent for a richer looking alert.
    """
    token   = SLACK_BOT_TOKEN
    channel = SLACK_CHANNEL_ID

    if not token or not channel:
        return "Slack not configured"

    color_map = {"P0": "#e53e3e", "P1": "#EF9F27", "P2": "#1D9E75"}
    emoji_map = {"P0": "🔴", "P1": "🟡", "P2": "🟢"}
    color = color_map.get(severity, "#888")
    emoji = emoji_map.get(severity, "⚪")

    # Only add war room link for P0
    war_room = ""
    if severity == "P0":
        war_room = f"\n*War room:* meet.google.com/crisis-{incident_id.lower()}"

    payload = {
        "channel": channel,
        "text": f"{emoji} [{severity}] {title}",   # fallback for notifications
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} [{severity}] {title}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Incident ID:*\n{incident_id}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Severity:*\n{severity}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*Agent assessment:*\n{triage_summary}"
                                f"{war_room}"
                            )
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "Sent by *CrisisOps AI* · Assign and resolve in dashboard"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10
        )
        result = response.json()
        if result.get("ok"):
            return "Rich Slack message sent"
        else:
            # Fall back to plain text if rich format fails
            print(f"[Slack] Rich message failed ({result.get('error')}), trying plain text")
            return post_to_slack(f"{emoji} [{severity}] {title}\n{triage_summary}")

    except Exception as e:
        print(f"[Slack] Error: {e}")
        return f"Slack failed: {str(e)}"
