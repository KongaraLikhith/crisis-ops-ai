# backend/tools/calendar_tool.py
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def create_war_room(incident_id: str, title: str,
                    severity: str, duration_minutes: int = 60) -> str:
    """
    Creates a Google Calendar event with a Google Meet link.
    Only called for P0 incidents by the Comms agent.

    Setup required (one-time):
      1. Go to console.cloud.google.com
      2. Enable Google Calendar API
      3. Create OAuth 2.0 credentials (Desktop app)
      4. Download credentials.json → put in backend/ folder
      5. Run: python tools/calendar_tool.py
         (opens browser to authorize, saves token.json)
      6. After that, the function works automatically.

    Returns the Google Meet link or a fallback message.
    """
    if severity not in {"P1", "P2"}:
        return f"War room skipped — only created for major incidents (this is {severity})"

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

        now       = datetime.utcnow()
        start_iso = now.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        end_iso   = (now + timedelta(minutes=duration_minutes)).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

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
            # This tells Google to create a Meet link
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
            conferenceDataVersion=1,   # required to get Meet link
        ).execute()

        meet_link = created.get("hangoutLink", "")
        event_url = created.get("htmlLink", "")

        print(f"[Calendar] War room created: {meet_link}")
        return f"War room created: {meet_link} | Calendar event: {event_url}"

    except ImportError:
        print("[Calendar] Google libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib")
        return _fallback_war_room(incident_id, title)
    except Exception as e:
        print(f"[Calendar] Error creating war room: {e}")
        return _fallback_war_room(incident_id, title)


def _fallback_war_room(incident_id: str, title: str) -> str:
    """
    Returns a fake war room link for demo purposes when
    Google Calendar is not configured. Safe to use in demo.
    """
    fake_id   = incident_id.lower().replace("inc-", "")
    fake_link = f"meet.google.com/crisis-{fake_id}"
    print(f"[Calendar] Using fallback war room link: {fake_link}")
    return f"War room (demo): {fake_link}"


# ── ONE-TIME SETUP ────────────────────────────────────────
# Run this file directly once to authorize Google Calendar:
#   python tools/calendar_tool.py
# It opens your browser, you sign in, and token.json is saved.
# After that, create_war_room() works without any browser.
if __name__ == "__main__":
    print("Running one-time Google Calendar authorization...")
    print("A browser window will open. Sign in with your Google account.")
    result = create_war_room(
        incident_id="TEST-001",
        title="Test War Room — please ignore",
        severity="P0",
        duration_minutes=30
    )
    print(f"Result: {result}")
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
