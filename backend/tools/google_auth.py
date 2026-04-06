# backend/tools/google_auth.py
# ── Shared OAuth helper for all Google Workspace MCP tools ────────────
# Manages a single token.json with combined scopes for
# Gmail, Calendar, Docs, and Sheets APIs.
# ──────────────────────────────────────────────────────────────────────
import os

# All scopes needed across every MCP tool
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Paths relative to backend/ directory
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
CREDS_PATH   = os.path.join(_BACKEND_DIR, "credentials.json")
TOKEN_PATH   = os.path.join(_BACKEND_DIR, "token.json")


def get_google_creds():
    """
    Returns authenticated Google OAuth2 credentials.
    If credentials.json doesn't exist, returns None (tool should fallback).
    On first run, opens a browser window for user consent.
    Subsequent runs reuse/refresh the saved token.json.
    """
    if not os.path.exists(CREDS_PATH):
        print("[GoogleAuth] credentials.json not found — Google Workspace tools will use fallback mode.")
        print("[GoogleAuth] To enable: download OAuth credentials from Google Cloud Console → save as backend/credentials.json")
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        creds = None

        # Load saved token if it exists
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        # Refresh or re-authorize if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the token for next time
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        return creds

    except ImportError:
        print("[GoogleAuth] Google auth libraries not installed.")
        print("[GoogleAuth] Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        return None
    except Exception as e:
        print(f"[GoogleAuth] Error getting credentials: {e}")
        return None


# ── One-time setup CLI ────────────────────────────────────────────────
# Run this file directly to authorize all scopes at once:
#   python tools/google_auth.py
if __name__ == "__main__":
    print("=" * 60)
    print("CrisisOps AI — Google Workspace Authorization")
    print("=" * 60)
    print()
    print("This will authorize the following services:")
    print("  • Gmail (send incident alerts)")
    print("  • Google Calendar (create war rooms)")
    print("  • Google Docs (create incident tickets)")
    print("  • Google Sheets (live timeline)")
    print()
    print("A browser window will open. Sign in with your Google account.")
    print()

    creds = get_google_creds()
    if creds:
        print()
        print("✅ Authorization successful! Token saved to token.json")
        print("   All MCP tools are now ready to use.")
    else:
        print()
        print("❌ Authorization failed. Make sure credentials.json exists.")
