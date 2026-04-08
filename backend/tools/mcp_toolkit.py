import os
import logging
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from google.auth import default
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

PARENT_FOLDER_ID               = os.getenv("PARENT_FOLDER_ID")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_CALENDAR_ID             = os.getenv("GOOGLE_CALENDAR_ID", "primary")


class GoogleMCPToolkit:
    """
    Central toolkit for Google Workspace integrations (Gmail, Calendar, Docs, Sheets, Drive).
    Wraps tools as ADK FunctionTools for agent consumption.
    All methods are synchronous — FunctionTool does not support async.
    """

    def __init__(self):
        self.creds            = None
        self.gmail_service    = None
        self.calendar_service = None
        self.docs_service     = None
        self.sheets_service   = None
        self.drive_service    = None
        self._init_services()

    def _init_services(self):
        """Initialize all Google API services from service account or ADC."""
        try:
            scopes = [
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/gmail.send",
            ]

            if GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
                self.creds = service_account.Credentials.from_service_account_file(
                    GOOGLE_APPLICATION_CREDENTIALS, scopes=scopes
                )
                logger.info("[MCP] Loaded credentials from %s", GOOGLE_APPLICATION_CREDENTIALS)
            else:
                self.creds, _ = default(scopes=scopes)
                logger.info("[MCP] Using default application credentials")

            self.gmail_service    = build("gmail",    "v1", credentials=self.creds, cache_discovery=False)
            self.calendar_service = build("calendar", "v3", credentials=self.creds, cache_discovery=False)
            self.docs_service     = build("docs",     "v1", credentials=self.creds, cache_discovery=False)
            self.sheets_service   = build("sheets",   "v4", credentials=self.creds, cache_discovery=False)
            self.drive_service    = build("drive",    "v3", credentials=self.creds, cache_discovery=False)
            logger.info("[MCP] Google Workspace services initialized successfully.")
        except Exception as e:
            logger.warning("[MCP] Failed to init Workspace services: %s", e)


    # -------------------------------------------------------------------------
    # Gmail
    # -------------------------------------------------------------------------

    def send_email(self, to: str, subject: str, body: str, html_body: str = "") -> dict:
        """Send a stakeholder alert email via Gmail API. Supports plain text and HTML."""
        logger.info("[Gmail] Sending email to %s | Subject: %s", to, subject)

        if not self.gmail_service:
            return {"status": "error", "message": "Gmail service not initialized"}

        try:
            if html_body:
                mime = MIMEMultipart("alternative")
                mime["to"] = to
                mime["subject"] = subject
                mime.attach(MIMEText(body, "plain"))
                mime.attach(MIMEText(html_body, "html"))
            else:
                mime = MIMEText(body, "plain")
                mime["to"] = to
                mime["subject"] = subject

            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            self.gmail_service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

            logger.info("[Gmail] Email sent successfully to %s", to)
            return {"status": "ok", "recipient": to, "subject": subject}
        except Exception as e:
            logger.warning("[Gmail] Error sending email: %s", e)
            return {"status": "error", "message": str(e)}


    # -------------------------------------------------------------------------
    # Calendar
    # -------------------------------------------------------------------------

    def create_event(
        self,
        title: str,
        description: str,
        attendees: List[str],
        start_time: str,
        duration_minutes: int = 30,
    ) -> dict:
        """
        Create a Google Calendar war-room event with a Google Meet link.
        start_time must be ISO 8601 e.g. '2026-04-08T19:00:00Z'.
        """
        logger.info("[Calendar] Creating event: %s", title)

        if not self.calendar_service:
            return {"status": "error", "message": "Calendar service not initialized"}

        try:
            start_dt   = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end_dt     = start_dt + timedelta(minutes=duration_minutes)
            request_id = f"{title.lower().replace(' ', '-')}-{int(start_dt.timestamp())}"

            event_body = {
                "summary":     title,
                "description": description,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
                "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "UTC"},
                "attendees": [{"email": a} for a in attendees if a],
                "conferenceData": {
                    "createRequest": {
                        "requestId": request_id,
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
            }

            created = (
                self.calendar_service.events()
                .insert(
                    calendarId=GOOGLE_CALENDAR_ID,
                    body=event_body,
                    conferenceDataVersion=1,
                    sendUpdates="all",
                )
                .execute()
            )

            logger.info("[Calendar] Event created: %s", created.get("id"))
            return {
                "status":     "ok",
                "event_id":   created.get("id",      ""),
                "event_link": created.get("htmlLink", ""),
                "meet_link":  "https://meet.google.com/abc-defg-hij",  # TODO: replace with real link
            }
        except Exception as e:
            logger.warning("[Calendar] Error creating event: %s", e)
            return {"status": "error", "message": str(e)}


    # -------------------------------------------------------------------------
    # Google Docs
    # -------------------------------------------------------------------------

    def create_doc(self, title: str, content: str = "") -> dict:
        """
        Create a Google Doc inside PARENT_FOLDER_ID (if set), share publicly,
        and optionally seed with initial content.
        """
        logger.info("[Docs] Creating document: %s", title)

        if not self.drive_service or not self.docs_service:
            mock_id = f"mock_doc_{int(datetime.now().timestamp())}"
            logger.warning("[Docs] Drive/Docs not available, returning mock: %s", mock_id)
            return {"status": "ok", "doc_id": mock_id, "doc_url": "#", "url": "#"}

        try:
            file_metadata = {
                "name":     title,
                "mimeType": "application/vnd.google-apps.document",
            }
            if PARENT_FOLDER_ID:
                file_metadata["parents"] = [PARENT_FOLDER_ID]

            file   = self.drive_service.files().create(body=file_metadata, fields="id").execute()
            doc_id = file.get("id", "")

            try:
                self.drive_service.permissions().create(
                    fileId=doc_id,
                    body={"type": "anyone", "role": "writer"},
                ).execute()
            except Exception as pe:
                logger.warning("[Docs] Could not set public permissions: %s", pe)

            # Delegate all content writing to append_to_doc — avoids double-write
            if content:
                self.append_to_doc(doc_id, content)

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            logger.info("[Docs] Created and shared: %s", doc_url)
            return {
                "status":      "ok",
                "doc_id":      doc_id,
                "document_id": doc_id,
                "url":         doc_url,
                "doc_url":     doc_url,
            }
        except Exception as e:
            logger.warning("[Docs] Error creating document: %s", e)
            return {"status": "error", "message": str(e)}

    def append_to_doc(self, doc_id: str, content: str) -> dict:
        """
        Append text to the END of an existing Google Doc.
        Reads document length first so content is never prepended to the top.
        """
        logger.info("[Docs] Appending to document %s", doc_id)

        if not self.docs_service or doc_id.startswith("mock_"):
            return {"status": "ok", "doc_id": doc_id}

        try:
            doc          = self.docs_service.documents().get(documentId=doc_id).execute()
            body_content = doc.get("body", {}).get("content", [])
            end_index    = body_content[-1].get("endIndex", 2) - 1 if body_content else 1

            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={
                    "requests": [
                        {
                            "insertText": {
                                "location": {"index": end_index},
                                "text": content,
                            }
                        }
                    ]
                },
            ).execute()
            return {"status": "ok", "doc_id": doc_id}
        except Exception as e:
            logger.warning("[Docs] Error appending to document: %s", e)
            return {"status": "error", "message": str(e)}


    # -------------------------------------------------------------------------
    # Google Sheets
    # -------------------------------------------------------------------------

    def create_sheet(self, title: str, headers: List[str]) -> dict:
        """
        Create a Google Sheet inside PARENT_FOLDER_ID (if set), share publicly,
        and write the header row. Used for live incident timelines.
        """
        logger.info("[Sheets] Creating spreadsheet: %s", title)

        if not self.drive_service or not self.sheets_service:
            mock_id = f"mock_sheet_{int(datetime.now().timestamp())}"
            logger.warning("[Sheets] Drive/Sheets not available, returning mock: %s", mock_id)
            return {"status": "ok", "sheet_id": mock_id, "sheet_url": "#", "url": "#"}

        try:
            file_metadata = {
                "name":     title,
                "mimeType": "application/vnd.google-apps.spreadsheet",
            }
            if PARENT_FOLDER_ID:
                file_metadata["parents"] = [PARENT_FOLDER_ID]

            file     = self.drive_service.files().create(body=file_metadata, fields="id").execute()
            sheet_id = file.get("id", "")

            if headers:
                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range="Sheet1!A1",
                    valueInputOption="RAW",
                    body={"values": [headers]},
                ).execute()

            try:
                self.drive_service.permissions().create(
                    fileId=sheet_id,
                    body={"type": "anyone", "role": "writer"},
                ).execute()
            except Exception as pe:
                logger.warning("[Sheets] Could not set public permissions: %s", pe)

            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
            logger.info("[Sheets] Created and shared: %s", sheet_url)
            return {
                "status":    "ok",
                "sheet_id":  sheet_id,
                "url":       sheet_url,
                "sheet_url": sheet_url,
            }
        except Exception as e:
            logger.warning("[Sheets] Error creating spreadsheet: %s", e)
            return {"status": "error", "message": str(e)}

    def append_row(self, sheet_id: str, row_data: List) -> dict:
        """Append a timestamped row to log each agent action during an incident."""
        logger.info("[Sheets] Appending row to %s: %s", sheet_id, row_data)

        if not self.sheets_service or sheet_id.startswith("mock_"):
            return {"status": "ok", "sheet_id": sheet_id}

        try:
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range="Sheet1!A1",
                valueInputOption="RAW",
                body={"values": [row_data]},
            ).execute()
            return {"status": "ok", "sheet_id": sheet_id}
        except Exception as e:
            logger.warning("[Sheets] Error appending row: %s", e)
            return {"status": "error", "message": str(e)}


    # -------------------------------------------------------------------------
    # ADK tool registration
    # -------------------------------------------------------------------------

    def get_tools(self) -> List[FunctionTool]:
        """Wrap all methods as synchronous ADK FunctionTools for agent consumption."""
        return [
            FunctionTool(self.send_email),
            FunctionTool(self.create_event),
            FunctionTool(self.create_doc),
            FunctionTool(self.append_to_doc),
            FunctionTool(self.create_sheet),
            FunctionTool(self.append_row),
        ]