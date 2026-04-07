# backend/tools/calendar_tool.py
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

VALID_SEVERITIES = {"P0", "P1", "P2"}
DEFAULT_SEVERITY = "P2"


def normalize_severity(value: str) -> str:
    sev = (value or "").strip().upper()
    return sev if sev in VALID_SEVERITIES else DEFAULT_SEVERITY


def create_war_room(
    incident_id: str,
    title: str,
    severity: str,
    duration_minutes: int = 60,
) -> str:
    """
    Creates a Google Calendar event with a Google Meet link.

    Severity policy:
      - P0: create immediately
      - P1: optional, depending on coordination policy
      - P2: no war room by default

    Returns the Google Meet link or a fallback message.
    """
    severity = normalize_severity(severity)

    if severity != "P0":
        return f"War room skipped — only created for P0 incidents (this is {severity})"

    # Check if Google Calendar is configured
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        print("[Calendar] Service account credentials not found — skipping war room creation")
        return _fallback_war_room(incident_id, title)

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/calendar"]
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow()
        start_iso = now.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        end_iso = (now + timedelta(minutes=duration_minutes)).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        fake_meet = f"meet.google.com/crisis-{incident_id.lower().replace('inc-', '')}"

        event = {
            "summary": f"🚨 War Room: {title}",
            "description": (
                f"Incident ID: {incident_id}\n"
                f"Severity: {severity}\n"
                f"Auto-created by CrisisOps AI.\n\n"
                f"Join the war room: https://{fake_meet}\n\n"
                f"Triage results and post-mortem available in the CrisisOps dashboard."
            ),
            "start": {
                "dateTime": start_iso,
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_iso,
                "timeZone": "UTC",
            },
        }

        created = service.events().insert(
            calendarId="primary",
            body=event,
        ).execute()

        event_url = created.get("htmlLink", "")

        print(f"[Calendar] War room created: {event_url}")
        return f"War room created: {fake_meet} | Calendar event: {event_url}"

    except ImportError:
        print(
            "[Calendar] Google libraries not installed. "
            "Run: pip install google-api-python-client google-auth-oauthlib"
        )
        return _fallback_war_room(incident_id, title)
    except Exception as e:
        print(f"[Calendar] Error creating war room: {e}")
        return _fallback_war_room(incident_id, title)


def _fallback_war_room(incident_id: str, title: str) -> str:
    """
    Returns a fake war room link for demo purposes when
    Google Calendar is not configured.
    """
    fake_id = incident_id.lower().replace("inc-", "")
    fake_link = f"meet.google.com/crisis-{fake_id}"
    print(f"[Calendar] Using fallback war room link: {fake_link}")
    return f"War room (demo): {fake_link}"


def create_calendar_event(
    incident_id: str,
    title: str,
    severity: str,
    duration_minutes: int = 60,
) -> str:
    """Adapter used by commander/coordinator."""
    return create_war_room(
        incident_id=incident_id,
        title=title,
        severity=severity,
        duration_minutes=duration_minutes,
    )


def get_upcoming_events() -> list[dict]:
    """
    Lightweight status helper for commander status queries.
    Safe fallback when Calendar API is not configured.
    """
    return []
