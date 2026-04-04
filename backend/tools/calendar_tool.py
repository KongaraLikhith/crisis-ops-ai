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
    if severity != "P0":
        return f"War room skipped — only created for P0 (this is {severity})"

    # Check if Google Calendar is configured
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

        SCOPES = ["https://www.googleapis.com/auth/calendar"]
        creds  = None

        # Load saved token if it exists
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Refresh or re-authorize if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the token for next time
            with open(token_path, "w") as f:
                f.write(creds.to_json())

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
