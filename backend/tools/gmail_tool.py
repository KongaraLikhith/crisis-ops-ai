# backend/tools/gmail_tool.py
# ── Gmail MCP Tool ───────────────────────────────────────────────────
# Sends emails via Gmail API using OAuth credentials.
# Used by the Communication Agent for stakeholder alerts.
#
# Setup: run `python tools/google_auth.py` once to authorize.
# ─────────────────────────────────────────────────────────────────────
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from tools.google_auth import get_google_creds


def send_email(to, subject, body, html_body=""):
    """
    Sends an email via Gmail API.

    Args:
        to:        recipient email (str) or list of emails
        subject:   email subject line
        body:      plain text body
        html_body: optional HTML body (if provided, sends multipart)

    Returns:
        dict: {"status": "ok"/"error", "result": ...}
    """
    creds = get_google_creds()

    if not creds:
        # Fallback: log to console for demo
        print(f"[Gmail] FALLBACK — would send email:")
        print(f"  To:      {to}")
        print(f"  Subject: {subject}")
        print(f"  Body:    {body[:200]}...")
        return {
            "status": "ok",
            "result": "Email logged to console (Gmail not configured)",
            "fallback": True
        }

    try:
        from googleapiclient.discovery import build

        service = build("gmail", "v1", credentials=creds)

        # Handle list of recipients
        if isinstance(to, list):
            to_str = ", ".join(to)
        else:
            to_str = to

        # Build the message
        if html_body:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
        else:
            msg = MIMEText(body)

        msg["to"] = to_str
        msg["subject"] = subject

        # Encode and send
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

        message_id = result.get("id", "unknown")
        print(f"[Gmail] Email sent successfully (ID: {message_id})")

        return {
            "status": "ok",
            "result": f"Email sent to {to_str}",
            "message_id": message_id
        }

    except ImportError:
        print("[Gmail] google-api-python-client not installed")
        return {"status": "error", "result": "Gmail library not installed"}
    except Exception as e:
        print(f"[Gmail] Error sending email: {e}")
        return {"status": "error", "result": str(e)}


def send_incident_alert(incident_id, title, severity, summary=""):
    """
    Convenience function: sends a formatted incident alert email.
    Used directly by the Comms agent.
    """
    emoji_map = {"P0": "🔴", "P1": "🟡", "P2": "🟢"}
    emoji = emoji_map.get(severity, "⚪")

    subject = f"{emoji} [{severity}] {title}"

    body = f"""CrisisOps AI — Incident Alert

{emoji} [{severity}] {title}

Incident ID: {incident_id}
Severity: {severity}

{summary if summary else 'Investigation in progress.'}

— CrisisOps AI (automated alert)
"""

    html_body = f"""
<div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
  <div style="background: {'#fee2e2' if severity == 'P0' else '#fef3c7' if severity == 'P1' else '#d1fae5'};
              border-left: 4px solid {'#dc2626' if severity == 'P0' else '#d97706' if severity == 'P1' else '#059669'};
              padding: 16px; border-radius: 8px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px 0; font-size: 18px;">
      {emoji} [{severity}] {title}
    </h2>
    <p style="margin: 0; color: #6b7280; font-size: 14px;">
      Incident ID: <code>{incident_id}</code>
    </p>
  </div>
  <div style="padding: 16px; background: #f9fafb; border-radius: 8px;">
    <p style="margin: 0 0 12px 0; font-size: 14px; color: #374151;">
      {summary if summary else 'Investigation in progress. Agents are analyzing the issue.'}
    </p>
  </div>
  <p style="color: #9ca3af; font-size: 12px; margin-top: 16px;">
    Sent by CrisisOps AI · Assign and resolve in dashboard
  </p>
</div>
"""

    # For demo, send to a default address. In production, this would
    # come from get_contacts_by_team() in the DB.
    import os
    recipient = os.getenv("ALERT_EMAIL", "team@example.com")

    return send_email(
        to=recipient,
        subject=subject,
        body=body,
        html_body=html_body
    )


# ── CLI test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Gmail MCP tool...")
    result = send_incident_alert(
        incident_id="TEST-001",
        title="Test Alert — please ignore",
        severity="P1",
        summary="This is a test email from CrisisOps AI."
    )
    print(f"Result: {result}")
