# backend/tools/sheets_tool.py
# ── Google Sheets MCP Tool ───────────────────────────────────────────
# Creates spreadsheets and appends rows for live incident timelines.
# Used by the Documentation Agent.
#
# Setup: run `python tools/google_auth.py` once to authorize.
# ─────────────────────────────────────────────────────────────────────
from tools.google_auth import get_google_creds


def create_sheet(title, headers):
    """
    Creates a new Google Sheet with the given title and header row.

    Args:
        title:   spreadsheet title
        headers: list of column header strings

    Returns:
        dict: {"status": "ok"/"error", "result": ..., "sheet_id": ...}
    """
    creds = get_google_creds()

    if not creds:
        print(f"[Sheets] FALLBACK — would create sheet:")
        print(f"  Title:   {title}")
        print(f"  Headers: {headers}")
        return {
            "status": "ok",
            "result": f"Sheet '{title}' logged to console (Sheets not configured)",
            "sheet_id": f"DEMO-SHEET-{title[:10].replace(' ', '-').upper()}",
            "sheet_url": None,
            "fallback": True
        }

    try:
        from googleapiclient.discovery import build

        service = build("sheets", "v4", credentials=creds)

        # Create the spreadsheet
        spreadsheet = service.spreadsheets().create(
            body={
                "properties": {"title": title},
                "sheets": [{"properties": {"title": "Timeline"}}]
            }
        ).execute()

        sheet_id = spreadsheet["spreadsheetId"]
        sheet_url = spreadsheet["spreadsheetUrl"]

        # Write header row
        if headers:
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range="Timeline!A1",
                valueInputOption="RAW",
                body={"values": [headers]}
            ).execute()

        print(f"[Sheets] Spreadsheet created: {sheet_url}")

        return {
            "status": "ok",
            "result": f"Sheet '{title}' created with {len(headers)} columns",
            "sheet_id": sheet_id,
            "sheet_url": sheet_url
        }

    except ImportError:
        print("[Sheets] google-api-python-client not installed")
        return {"status": "error", "result": "Sheets library not installed", "sheet_id": None}
    except Exception as e:
        print(f"[Sheets] Error creating spreadsheet: {e}")
        return {"status": "error", "result": str(e), "sheet_id": None}


def append_row(sheet_id, row_data):
    """
    Appends a single row of data to an existing Google Sheet.

    Args:
        sheet_id: Google Spreadsheet ID
        row_data: list of values for the row

    Returns:
        dict: {"status": "ok"/"error", "result": ...}
    """
    creds = get_google_creds()

    if not creds:
        print(f"[Sheets] FALLBACK — would append row to {sheet_id}:")
        print(f"  Data: {row_data}")
        return {
            "status": "ok",
            "result": "Row logged to console (Sheets not configured)",
            "fallback": True
        }

    try:
        from googleapiclient.discovery import build

        service = build("sheets", "v4", credentials=creds)

        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Timeline!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_data]}
        ).execute()

        print(f"[Sheets] Row appended to {sheet_id}")
        return {"status": "ok", "result": f"Row appended ({len(row_data)} cells)"}

    except ImportError:
        print("[Sheets] google-api-python-client not installed")
        return {"status": "error", "result": "Sheets library not installed"}
    except Exception as e:
        print(f"[Sheets] Error appending row: {e}")
        return {"status": "error", "result": str(e)}


def create_timeline_sheet(incident_id, title, severity):
    """
    Convenience: creates a formatted incident timeline spreadsheet.
    """
    return create_sheet(
        title=f"Timeline — [{severity}] {title} ({incident_id})",
        headers=["Timestamp", "Agent", "Action", "Detail", "Status"]
    )


# ── CLI test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    from datetime import datetime

    print("Testing Google Sheets MCP tool...")

    # Test create
    result = create_timeline_sheet("TEST-001", "Test Incident", "P1")
    print(f"Create result: {result}")

    # Test append
    if result.get("sheet_id"):
        row_result = append_row(
            sheet_id=result["sheet_id"],
            row_data=[
                datetime.utcnow().isoformat(),
                "Commander",
                "Severity classified",
                "P1",
                "done"
            ]
        )
        print(f"Append result: {row_result}")
