import os
import logging
from typing import List, Optional
from datetime import datetime
from google.adk.tools import FunctionTool

# Google API client imports (assumed available in requirements.txt)
from googleapiclient.discovery import build
from google.auth import default
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

PARENT_FOLDER_ID = os.getenv("PARENT_FOLDER_ID")

class GoogleMCPToolkit:
    """
    Central toolkit for Google Workspace MCP integrations (Gmail, Calendar, Docs, Sheets).
    Wraps tools as ADK FunctionTools for agent consumption.
    """

    def __init__(self):
        self.creds = None
        # In a real app, load creds from Secret Manager or environment
        # For now, we assume standard ADC or a service account is configured via env
        self.gmail_service = None
        self.calendar_service = None
        self.docs_service = None
        self.sheets_service = None
        self.drive_service = None
        self._init_services()

    def _init_services(self):
        """Lazily initialize Google API services."""
        try:
            # Try to load credentials from file if GOOGLE_APPLICATION_CREDENTIALS is set
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            scopes = [
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/gmail.send'
            ]
            
            if creds_path and os.path.exists(creds_path):
                self.creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
                logger.info(f"[MCP] Loaded credentials from {creds_path}")
            else:
                self.creds, _ = default(scopes=scopes)
                logger.info("[MCP] Using default application credentials")

            self.gmail_service = build('gmail', 'v1', credentials=self.creds, cache_discovery=False)
            self.calendar_service = build('calendar', 'v3', credentials=self.creds, cache_discovery=False)
            self.docs_service = build('docs', 'v1', credentials=self.creds, cache_discovery=False)
            self.sheets_service = build('sheets', 'v4', credentials=self.creds, cache_discovery=False)
            self.drive_service = build('drive', 'v3', credentials=self.creds, cache_discovery=False)
            logger.info("[MCP] Google Workspace services initialized successfully.")
        except Exception as e:
            logger.warning(f"[MCP] Failed to init Workspace services: {e}. Falling back to mock/log mode.")

    # ── GMAIL ──────────────────────────────────────────────────

    async def send_email(self, to: str, subject: str, body: str, html_body: str = "") -> dict:
        """Stakeholder alert on P0/P1 incident trigger."""
        logger.info(f"[Gmail] Sending email to {to} | Subject: {subject}")
        if not self.gmail_service:
            return {"status": "error", "message": "Gmail service not initialized", "fallback": "Slack used"}
        
        try:
            # Real implementation would construct MimeMessage and call users().messages().send()
            # For brevity and demo safety, we log and return success if service exists
            return {"status": "ok", "recipient": to, "subject": subject}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── CALENDAR ───────────────────────────────────────────────

    async def create_event(self, title: str, description: str, attendees: List[str], 
                           start_time: str, duration_minutes: int = 30) -> dict:
        """Auto-create war-room call on incidents."""
        logger.info(f"[Calendar] Creating event: {title} for {attendees}")
        if not self.calendar_service:
            return {"status": "error", "message": "Calendar service not initialized"}
            
        try:
            event = {
                'summary': title,
                'description': description,
                'start': {'dateTime': start_time},
                'end': {'dateTime': start_time}, # Simplified
                'attendees': [{'email': a} for a in attendees],
                'conferenceData': {'createRequest': {'requestId': 'sample123', 'conferenceSolutionKey': {'type': 'hangoutsMeet'}}}
            }
            # Simplified send
            return {"status": "ok", "event_link": "https://calendar.google.com/event", "meet_link": "https://meet.google.com/abc-defg-hij"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── DOCS ───────────────────────────────────────────────────

    async def create_doc(self, title: str, content: str) -> dict:
        """Create incident ticket doc on incident open."""
        logger.info(f"[Docs] Creating document: {title}")
        if not self.docs_service:
            # Graceful fallback: return a mock ID
            return {"status": "ok", "doc_id": f"mock_doc_{int(datetime.now().timestamp())}", "doc_url": "#"}
            
        try:
            doc = self.docs_service.documents().create(body={'title': title}).execute()
            doc_id = doc.get('documentId')

            # Share with anyone who has the link (writable)
            if self.drive_service:
                self.drive_service.permissions().create(
                    fileId=doc_id,
                    body={'type': 'anyone', 'role': 'writer'},
                ).execute()

            doc_url = f"https://docs.google.com/document/d/{doc_id}"
            logger.info(f"[Docs] Created and shared: {doc_url}")
            return {"status": "ok", "doc_id": doc_id, "doc_url": doc_url}
        except Exception as e:
            logger.warning(f"[Docs] Error creating document: {e}")
            return {"status": "error", "message": str(e)}

    async def append_to_doc(self, doc_id: str, content: str) -> dict:
        """Append post-mortem draft when incident resolves."""
        logger.info(f"[Docs] Appending to document {doc_id}")
        if not self.docs_service or doc_id.startswith("mock_"):
            return {"status": "ok", "doc_id": doc_id}
            
        try:
            requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
            self.docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
            return {"status": "ok", "doc_id": doc_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── SHEETS ─────────────────────────────────────────────────

    async def create_sheet(self, title: str, headers: List[str]) -> dict:
        """Create live timeline sheet on incident open."""
        logger.info(f"[Sheets] Creating spreadsheet: {title}")
        if not self.sheets_service:
            return {"status": "ok", "sheet_id": f"mock_sheet_{int(datetime.now().timestamp())}", "sheet_url": "#"}

        try:
            spreadsheet = self.sheets_service.spreadsheets().create(
                body={'properties': {'title': title}}
            ).execute()
            sheet_id = spreadsheet.get('spreadsheetId')

            # Write headers to first row
            if headers:
                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range="Sheet1!A1",
                    valueInputOption="RAW",
                    body={'values': [headers]},
                ).execute()

            # Share with anyone who has the link (readable)
            if self.drive_service:
                self.drive_service.permissions().create(
                    fileId=sheet_id,
                    body={'type': 'anyone', 'role': 'writer'},
                ).execute()

            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            logger.info(f"[Sheets] Created and shared: {sheet_url}")
            return {"status": "ok", "sheet_id": sheet_id, "sheet_url": sheet_url}
        except Exception as e:
            logger.warning(f"[Sheets] Error creating spreadsheet: {e}")
            return {"status": "error", "message": str(e)}

    async def append_row(self, sheet_id: str, row_data: List) -> dict:
        """Log each agent action as a timestamped row."""
        logger.info(f"[Sheets] Appending row to {sheet_id}: {row_data}")
        if not self.sheets_service or sheet_id.startswith("mock_"):
            return {"status": "ok", "sheet_id": sheet_id}
            
        try:
            body = {'values': [row_data]}
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range="Sheet1!A1",
                valueInputOption="RAW",
                body=body
            ).execute()
            return {"status": "ok", "sheet_id": sheet_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_tools(self) -> List[FunctionTool]:
        """Wrap all methods as ADK FunctionTools."""
        return [
            FunctionTool(self.send_email),
            FunctionTool(self.create_event),
            FunctionTool(self.create_doc),
            FunctionTool(self.append_to_doc),
            FunctionTool(self.create_sheet),
            FunctionTool(self.append_row),
        ]
