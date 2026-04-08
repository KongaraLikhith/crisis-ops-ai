import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_DEFAULT_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
SLACK_BOT_USER_ID = os.getenv("SLACK_BOT_USER_ID")
SLACK_DEFAULT_INVITEES = os.getenv("SLACK_DEFAULT_INVITEES", "").strip()

VALID_SEVERITIES = {"P0", "P1", "P2"}
DEFAULT_SEVERITY = "P2"
SLACK_API_BASE = "https://slack.com/api"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def normalize_severity(value: str) -> str:
    sev = (value or "").strip().upper()
    return sev if sev in VALID_SEVERITIES else DEFAULT_SEVERITY


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }


def _slack_api(method: str, payload: dict) -> dict:
    if not SLACK_BOT_TOKEN:
        return {"ok": False, "error": "missing_slack_token"}
    try:
        response = requests.post(
            f"{SLACK_API_BASE}/{method}",
            headers=_auth_headers(),
            json=payload,
            timeout=15,
        )
        data = response.json()
        if not data.get("ok"):
            print(f"[Slack] {method} failed: {data.get('error', 'unknown_error')}")
        return data
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _clean_channel_name(name: str) -> str:
    cleaned = (name or "").strip().lower().lstrip("#")
    cleaned = re.sub(r"[^a-z0-9_-]", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned[:80] or "incident-room"


def resolve_slack_channel(channel: str | None = None) -> str | None:
    resolved = (channel or "").strip() or (SLACK_DEFAULT_CHANNEL_ID or "").strip()
    return resolved or None


# -----------------------------------------------------------------------------
# Messaging
# -----------------------------------------------------------------------------

def send_slack_message(message: str, channel: str | None = None) -> str:
    """Send a plain-text message to a Slack channel."""
    resolved_channel = resolve_slack_channel(channel)

    if not SLACK_BOT_TOKEN:
        print("[Slack] Missing SLACK_BOT_TOKEN")
        return "Slack error: missing_slack_token"

    if not resolved_channel:
        print("[Slack] Missing Slack channel")
        return "Slack error: missing_channel"

    result = _slack_api(
        "chat.postMessage",
        {
            "channel": resolved_channel,
            "text": message,
            "unfurl_links": False,
            "unfurl_media": False,
        },
    )

    if result.get("ok"):
        print(f"[Slack] Message sent to {resolved_channel}")
        return "Slack message sent"

    error = result.get("error", "unknown_error")
    return f"Slack error: {error}"


def post_rich_slack_message(
    incident_id: str,
    title: str,
    severity: str,
    triage_summary: str,
    channel: str | None = None,
    war_room_link: str | None = None,
    doc_url: str | None = None,
    sheet_url: str | None = None,
) -> str:
    """
    Send a formatted incident alert to Slack using Block Kit.
    Links use Slack mrkdwn <URL|label> format — never truncated, always clickable.
    Falls back to plain text if the rich message fails.
    """
    resolved_channel = resolve_slack_channel(channel)
    severity = normalize_severity(severity)

    if not SLACK_BOT_TOKEN:
        return "Slack error: missing_slack_token"

    if not resolved_channel:
        return "Slack error: missing_channel"

    color_map = {"P0": "#e53e3e", "P1": "#EF9F27", "P2": "#1D9E75"}
    emoji_map = {
        "P0": ":red_circle:",
        "P1": ":large_orange_circle:",
        "P2": ":large_green_circle:",
    }

    color = color_map.get(severity, "#888888")
    emoji = emoji_map.get(severity, ":white_circle:")

    # Slack mrkdwn <URL|label> format — renders as labelled hyperlink, never truncated
    links = []
    if war_room_link and war_room_link not in ("", "not available"):
        links.append(f"<{war_room_link}|:video_camera:  Join War Room>")
    if doc_url and doc_url not in ("", "not available"):
        links.append(f"<{doc_url}|:page_facing_up:  Incident Doc>")
    if sheet_url and sheet_url not in ("", "not available"):
        links.append(f"<{sheet_url}|:bar_chart:  Timeline Sheet>")

    link_block_text = (
        "    ".join(links) if links else "_No coordination links available yet._"
    )

    payload = {
        "channel": resolved_channel,
        "text": f"{emoji} [{severity}] {title}",
        "unfurl_links": False,
        "unfurl_media": False,
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"[{severity}] {title}",
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
                                "text": f"*Severity:*\n{emoji}  {severity}",
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Agent assessment:*\n{triage_summary}",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": link_block_text,
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "Sent by *CrisisOps AI*",
                            }
                        ],
                    },
                ],
            }
        ],
    }

    result = _slack_api("chat.postMessage", payload)

    if result.get("ok"):
        print(f"[Slack] Rich message sent to {resolved_channel}")
        return "Rich Slack message sent"

    error = result.get("error", "unknown_error")
    print(f"[Slack] Rich message failed ({error}), falling back to plain text")

    fallback_lines = "\n".join(filter(None, [war_room_link, doc_url, sheet_url]))
    fallback = (
        f"{emoji} [{severity}] {title}\n\n"
        f"Incident ID: {incident_id}\n"
        f"{triage_summary}\n\n"
        f"{fallback_lines}"
    ).strip()

    return send_slack_message(fallback, channel=resolved_channel)


# -----------------------------------------------------------------------------
# Channel management
# -----------------------------------------------------------------------------

def invite_bot_to_channel(channel_id: str) -> dict:
    """Invite the bot user into a channel so it can post messages."""
    if not SLACK_BOT_TOKEN:
        return {"ok": False, "error": "missing_slack_token"}
    if not channel_id:
        return {"ok": False, "error": "missing_channel_id"}
    if not SLACK_BOT_USER_ID:
        return {"ok": False, "error": "missing_bot_user_id"}

    return _slack_api(
        "conversations.invite",
        {"channel": channel_id, "users": SLACK_BOT_USER_ID},
    )


def find_channel_by_name(name: str) -> dict:
    """Look up a Slack channel by name, paginating through all results."""
    if not SLACK_BOT_TOKEN:
        return {"ok": False, "error": "missing_slack_token"}

    clean_name = _clean_channel_name(name)
    cursor = None

    while True:
        payload = {
            "limit": 200,
            "exclude_archived": True,
            "types": "public_channel,private_channel",
        }
        if cursor:
            payload["cursor"] = cursor

        result = _slack_api("conversations.list", payload)
        if not result.get("ok"):
            return {"ok": False, "error": result.get("error", "lookup_failed")}

        for ch in result.get("channels", []) or []:
            if ch.get("name") == clean_name:
                return {
                    "ok": True,
                    "channel_id": ch.get("id"),
                    "channel_name": f"#{ch.get('name')}",
                    "raw_channel_name": ch.get("name"),
                }

        cursor = (
            ((result.get("response_metadata") or {}).get("next_cursor")) or ""
        ).strip()
        if not cursor:
            break

    return {"ok": False, "error": "channel_not_found"}


def create_slack_channel(name: str, is_private: bool = False) -> dict:
    """
    Create a new Slack channel.
    After creation:
      - Invites the bot so it can post.
      - Invites human members from SLACK_DEFAULT_INVITEES so the channel
        appears in their sidebar.
    If the channel name is already taken, returns the existing channel.
    """
    if not SLACK_BOT_TOKEN:
        return {"ok": False, "error": "missing_slack_token"}

    clean_name = _clean_channel_name(name)

    result = _slack_api(
        "conversations.create",
        {"name": clean_name, "is_private": is_private},
    )

    if result.get("ok"):
        channel = result.get("channel", {}) or {}
        channel_id = channel.get("id")
        channel_name = channel.get("name", clean_name)

        # Invite the bot into the channel
        if channel_id and SLACK_BOT_USER_ID:
            bot_result = invite_bot_to_channel(channel_id)
            if not bot_result.get("ok"):
                print(f"[Slack] Bot invite warning: {bot_result.get('error')}")

        # Invite human members so the channel appears in their sidebar
        if channel_id and SLACK_DEFAULT_INVITEES:
            human_result = _slack_api(
                "conversations.invite",
                {"channel": channel_id, "users": SLACK_DEFAULT_INVITEES},
            )
            if not human_result.get("ok"):
                print(f"[Slack] Human invite warning: {human_result.get('error')}")

        print(f"[Slack] Channel created: #{channel_name} ({channel_id})")
        return {
            "ok": True,
            "channel_id": channel_id,
            "channel_name": f"#{channel_name}",
            "raw_channel_name": channel_name,
        }

    error = result.get("error", "unknown_error")

    # Channel already exists — look it up and return it
    if error == "name_taken":
        lookup = find_channel_by_name(clean_name)
        if lookup.get("ok"):
            print(f"[Slack] Channel already exists, reusing: {lookup.get('channel_name')}")
            return lookup

    return {"ok": False, "error": error}


def ensure_incident_channel(name: str, is_private: bool = False) -> dict:
    """
    Idempotent: returns existing channel or creates a new one.
    Delegates entirely to create_slack_channel which handles name_taken internally.
    """
    return create_slack_channel(name=name, is_private=is_private)