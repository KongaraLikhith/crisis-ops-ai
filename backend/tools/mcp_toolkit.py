# backend/tools/mcp_toolkit.py
# ── Unified Google Workspace MCP Toolkit ─────────────────────────────
# Single entry point that wraps all Google Workspace tool functions.
# Import once, use everywhere.
#
# Usage:
#   from tools.mcp_toolkit import toolkit
#   toolkit.send_email(to="...", subject="...", body="...")
#   toolkit.create_doc(title="...", content="...")
# ─────────────────────────────────────────────────────────────────────


class GoogleMCPToolkit:
    """
    Unified toolkit exposing all Google Workspace MCP tools.
    Each tool returns: {"status": "ok"/"error", "result": ...}
    All tools have graceful fallbacks when credentials aren't configured.
    """

    # ── Gmail ────────────────────────────────────────────────
    @staticmethod
    def send_email(to, subject, body, html_body=""):
        from tools.gmail_tool import send_email
        return send_email(to, subject, body, html_body)

    @staticmethod
    def send_incident_alert(incident_id, title, severity, summary=""):
        from tools.gmail_tool import send_incident_alert
        return send_incident_alert(incident_id, title, severity, summary)

    # ── Google Calendar ──────────────────────────────────────
    @staticmethod
    def create_war_room(incident_id, title, severity, duration_minutes=60):
        from tools.calendar_tool import create_war_room
        return create_war_room(incident_id, title, severity, duration_minutes)

    # ── Google Docs ──────────────────────────────────────────
    @staticmethod
    def create_doc(title, content):
        from tools.docs_tool import create_doc
        return create_doc(title, content)

    @staticmethod
    def append_to_doc(doc_id, content):
        from tools.docs_tool import append_to_doc
        return append_to_doc(doc_id, content)

    @staticmethod
    def create_incident_doc(incident_id, title, severity, description=""):
        from tools.docs_tool import create_incident_doc
        return create_incident_doc(incident_id, title, severity, description)

    # ── Google Sheets ────────────────────────────────────────
    @staticmethod
    def create_sheet(title, headers):
        from tools.sheets_tool import create_sheet
        return create_sheet(title, headers)

    @staticmethod
    def append_row(sheet_id, row_data):
        from tools.sheets_tool import append_row
        return append_row(sheet_id, row_data)

    @staticmethod
    def create_timeline_sheet(incident_id, title, severity):
        from tools.sheets_tool import create_timeline_sheet
        return create_timeline_sheet(incident_id, title, severity)

    # ── Slack (existing) ─────────────────────────────────────
    @staticmethod
    def post_to_slack(message, channel=None):
        from tools.slack_tool import post_to_slack
        return post_to_slack(message, channel)

    @staticmethod
    def post_rich_slack_message(incident_id, title, severity, triage_summary):
        from tools.slack_tool import post_rich_slack_message
        return post_rich_slack_message(incident_id, title, severity, triage_summary)

    # ── DB Tools (existing) ─────────────────────────────────
    @staticmethod
    def log_action(incident_id, agent, action, detail):
        from tools.db_tools import log_action
        return log_action(incident_id, agent, action, detail)

    # ── Health check ─────────────────────────────────────────
    @staticmethod
    def check_status():
        """Returns a dict of which tools are available."""
        import os
        creds_path = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
        has_creds = os.path.exists(creds_path)

        slack_token = os.getenv("SLACK_BOT_TOKEN")
        has_slack = bool(slack_token and slack_token != "your_token")

        return {
            "google_workspace": has_creds,
            "gmail": has_creds,
            "calendar": has_creds,
            "docs": has_creds,
            "sheets": has_creds,
            "slack": has_slack,
            "notes": "All tools work in fallback mode without credentials"
        }


# Singleton instance — import this
toolkit = GoogleMCPToolkit()


# ── CLI: check what's available ──────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 50)
    print("CrisisOps AI — MCP Toolkit Status")
    print("=" * 50)

    status = toolkit.check_status()
    for key, value in status.items():
        if key == "notes":
            continue
        icon = "✅" if value else "⚠️  Fallback"
        print(f"  {key:20s} {icon}")

    print()
    print(f"Note: {status['notes']}")
