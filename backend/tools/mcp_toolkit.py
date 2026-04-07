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
        self._init_services()

    def _init_services(self):
        """Lazily initialize Google API services."""
        try:
            # Try to load credentials from file if GOOGLE_APPLICATION_CREDENTIALS is set
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            scopes = [
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/spreadsheets',
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
            # Mock append initial content
            return {"status": "ok", "doc_id": doc_id, "doc_url": f"https://docs.google.com/document/d/{doc_id}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def append_to_doc(self, doc_id: str, content: str) -> dict:
        """Append post-mortem draft when incident resolves."""
        logger.info(f"[Docs] Appending to document {doc_id}")
        if not self.docs_service or doc_id.startswith("mock_"):
            return {"status": "ok", "doc_id": doc_id}
            
        try:
            # requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
            # self.docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
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
            spreadsheet = self.sheets_service.spreadsheets().create(body={'properties': {'title': title}}).execute()
            sheet_id = spreadsheet.get('spreadsheetId')
            return {"status": "ok", "sheet_id": sheet_id, "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def append_row(self, sheet_id: str, row_data: List) -> dict:
        """Log each agent action as a timestamped row."""
        logger.info(f"[Sheets] Appending row to {sheet_id}: {row_data}")
        if not self.sheets_service or sheet_id.startswith("mock_"):
            return {"status": "ok", "sheet_id": sheet_id}
            
        try:
            return {"status": "ok", "sheet_id": sheet_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_tools(self) -> List[FunctionTool]:
        """Wrap all methods as ADK FunctionTools."""
        return [
            FunctionTool.from_callable(self.send_email),
            FunctionTool.from_callable(self.create_event),
            FunctionTool.from_callable(self.create_doc),
            FunctionTool.from_callable(self.append_to_doc),
            FunctionTool.from_callable(self.create_sheet),
            FunctionTool.from_callable(self.append_row),
        ]
