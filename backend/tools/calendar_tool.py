import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

VALID_SEVERITIES = {"P0", "P1", "P2"}
DEFAULT_SEVERITY = "P2"

GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def normalize_severity(value: str) -> str:
    sev = (value or "").strip().upper()
    return sev if sev in VALID_SEVERITIES else DEFAULT_SEVERITY


def _fallback_war_room(incident_id: str, title: str, reason: str = "") -> dict:
    fake_id = incident_id.lower().replace("inc-", "")
    fake_link = f"meet.google.com/crisis-{fake_id}"
    print(f"[Calendar] Using fallback war room link: {fake_link}")
    return {
        "ok": False,
        "fallback": True,
        "war_room_link": fake_link,
        "calendar_event_url": "",
        "calendar_event_id": "",
        "message": f"War room (demo): {fake_link}",
        "reason": reason or "calendar_unavailable",
    }


def _build_event_body(incident_id: str, title: str, severity: str, duration_minutes: int) -> dict:
    now = datetime.now(timezone.utc)
    end = now + timedelta(minutes=duration_minutes)

    war_room_link = f"https://meet.google.com/crisis-{incident_id.lower().replace('inc-', '')}"

    return {
        "summary": f"🚨 War Room: {title}",
        "description": (
            f"Incident ID: {incident_id}\n"
            f"Severity: {severity}\n"
            f"Auto-created by CrisisOps AI.\n\n"
            f"Join the war room: {war_room_link}\n\n"
            f"Triage results, docs, and updates are tracked in the CrisisOps dashboard."
        ),
        "start": {
            "dateTime": now.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": "UTC",
        },
        "conferenceData": {
            "createRequest": {
                "requestId": f"{incident_id.lower()}-{int(now.timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }


def create_war_room(
    incident_id: str,
    title: str,
    severity: str,
    duration_minutes: int = 60,
) -> dict:
    """
    Creates a Google Calendar event and attempts to attach a Google Meet link.

    Returns a dict so callers can save both the real link and any fallback.
    """
    severity = normalize_severity(severity)

    if severity == "P2":
        return {
            "ok": True,
            "skipped": True,
            "message": "War room skipped for P2 incidents",
            "war_room_link": "",
            "calendar_event_url": "",
            "calendar_event_id": "",
        }

    if not GOOGLE_APPLICATION_CREDENTIALS or not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        print("[Calendar] Service account credentials not found — skipping war room creation")
        return _fallback_war_room(incident_id, title, reason="missing_credentials")

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/calendar"]
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_APPLICATION_CREDENTIALS,
            scopes=scopes,
        )

        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        event_body = _build_event_body(incident_id, title, severity, duration_minutes)

        created = (
            service.events()
            .insert(
                calendarId=GOOGLE_CALENDAR_ID,
                body=event_body,
                conferenceDataVersion=1,
                sendUpdates="all",
            )
            .execute()
        )

        event_url = created.get("htmlLink", "")
        conference_data = created.get("conferenceData", {}) or {}
        entry_points = conference_data.get("entryPoints", []) or []
        meet_link = ""

        for entry in entry_points:
            if entry.get("entryPointType") == "video" and entry.get("uri"):
                meet_link = entry["uri"]
                break

        if not meet_link:
            meet_link = f"https://meet.google.com/crisis-{incident_id.lower().replace('inc-', '')}"

        print(f"[Calendar] War room created: {event_url}")
        return {
            "ok": True,
            "skipped": False,
            "message": f"War room created: {meet_link}",
            "war_room_link": meet_link,
            "calendar_event_url": event_url,
            "calendar_event_id": created.get("id", ""),
        }

    except ImportError:
        print(
            "[Calendar] Google libraries not installed. "
            "Run: pip install google-api-python-client google-auth"
        )
        return _fallback_war_room(incident_id, title, reason="missing_google_libs")
    except Exception as e:
        print(f"[Calendar] Error creating war room: {e}")
        return _fallback_war_room(incident_id, title, reason=str(e))


def create_calendar_event(
    incident_id: str,
    title: str,
    severity: str,
    duration_minutes: int = 60,
) -> dict:
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