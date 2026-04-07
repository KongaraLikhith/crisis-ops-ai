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

    creds_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
    token_path = os.path.join(os.path.dirname(__file__), "..", "token.json")

    if not os.path.exists(creds_path):
        print("[Calendar] credentials.json not found — skipping war room creation")
        return _fallback_war_room(incident_id, title)

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/calendar"]
        creds = None

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as f:
                f.write(creds.to_json())

        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow()
        start_iso = now.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        end_iso = (now + timedelta(minutes=duration_minutes)).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        event = {
            "summary": f"🚨 War Room: {title}",
            "description": (
                f"Incident ID: {incident_id}\n"
                f"Severity: {severity}\n"
                f"Auto-created by CrisisOps AI.\n\n"
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
            "conferenceData": {
                "createRequest": {
                    "requestId": incident_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        created = service.events().insert(
            calendarId="primary",
            body=event,
            conferenceDataVersion=1,
        ).execute()

        meet_link = created.get("hangoutLink", "")
        event_url = created.get("htmlLink", "")

        print(f"[Calendar] War room created: {meet_link}")
        return f"War room created: {meet_link} | Calendar event: {event_url}"

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


if __name__ == "__main__":
    print("Running one-time Google Calendar authorization...")
    print("A browser window will open. Sign in with your Google account.")
    result = create_war_room(
        incident_id="TEST-001",
        title="Test War Room — please ignore",
        severity="P0",
        duration_minutes=30,
    )
    print(f"Result: {result}")
