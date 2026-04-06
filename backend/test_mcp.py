# backend/test_mcp.py
# ── MCP Tools Test Suite ─────────────────────────────────────────────
# Tests each MCP tool independently + full integration test.
#
# Usage:
#   cd backend
#   python test_mcp.py          # run all tests
#   python test_mcp.py gmail    # test only gmail
#   python test_mcp.py docs     # test only docs
#   python test_mcp.py sheets   # test only sheets
#   python test_mcp.py toolkit  # test toolkit status
#   python test_mcp.py slack    # test slack
# ─────────────────────────────────────────────────────────────────────
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def hr(title=""):
    print(f"\n{'=' * 50}")
    if title:
        print(f"  {title}")
        print(f"{'=' * 50}")


def test_toolkit_status():
    """Check which tools are configured."""
    hr("TOOLKIT STATUS")
    from tools.mcp_toolkit import toolkit

    status = toolkit.check_status()
    for key, value in status.items():
        if key == "notes":
            continue
        icon = "✅" if value else "⚠️  Fallback"
        print(f"  {key:20s} {icon}")
    print(f"\n  Note: {status['notes']}")
    return True


def test_gmail():
    """Test Gmail MCP tool."""
    hr("GMAIL MCP TEST")
    from tools.gmail_tool import send_email, send_incident_alert

    # Test basic send
    print("\n[1] Testing send_email()...")
    result = send_email(
        to="test@example.com",
        subject="CrisisOps AI Test",
        body="This is a test email."
    )
    print(f"    Status: {result['status']}")
    print(f"    Result: {result['result']}")
    fallback = result.get("fallback", False)
    print(f"    Mode:   {'Fallback (no credentials)' if fallback else 'Live Gmail API'}")

    # Test incident alert
    print("\n[2] Testing send_incident_alert()...")
    result = send_incident_alert(
        incident_id="TEST-001",
        title="Test DB Outage",
        severity="P0",
        summary="Connection pool exhausted. All services down."
    )
    print(f"    Status: {result['status']}")
    print(f"    Result: {result['result']}")

    return result["status"] == "ok"


def test_docs():
    """Test Google Docs MCP tool."""
    hr("GOOGLE DOCS MCP TEST")
    from tools.docs_tool import create_doc, append_to_doc, create_incident_doc

    # Test create
    print("\n[1] Testing create_doc()...")
    result = create_doc(
        title="Test Document — CrisisOps",
        content="This is a test document content."
    )
    print(f"    Status:  {result['status']}")
    print(f"    Doc ID:  {result.get('doc_id')}")
    print(f"    Doc URL: {result.get('doc_url', 'N/A')}")

    # Test append
    doc_id = result.get("doc_id")
    if doc_id:
        print("\n[2] Testing append_to_doc()...")
        append_result = append_to_doc(
            doc_id=doc_id,
            content="\n\n## Appended Section\nThis was appended by the test suite."
        )
        print(f"    Status: {append_result['status']}")
        print(f"    Result: {append_result['result']}")

    # Test incident doc convenience
    print("\n[3] Testing create_incident_doc()...")
    inc_result = create_incident_doc(
        incident_id="TEST-002",
        title="Auth Service Down",
        severity="P1",
        description="JWT validation failing after deploy."
    )
    print(f"    Status:  {inc_result['status']}")
    print(f"    Doc ID:  {inc_result.get('doc_id')}")

    return result["status"] == "ok"


def test_sheets():
    """Test Google Sheets MCP tool."""
    hr("GOOGLE SHEETS MCP TEST")
    from tools.sheets_tool import create_sheet, append_row, create_timeline_sheet

    # Test create
    print("\n[1] Testing create_sheet()...")
    result = create_sheet(
        title="Test Timeline — CrisisOps",
        headers=["Timestamp", "Agent", "Action", "Detail", "Status"]
    )
    print(f"    Status:   {result['status']}")
    print(f"    Sheet ID: {result.get('sheet_id')}")
    print(f"    URL:      {result.get('sheet_url', 'N/A')}")

    # Test append
    sheet_id = result.get("sheet_id")
    if sheet_id:
        print("\n[2] Testing append_row()...")
        now = datetime.utcnow().isoformat()
        row_result = append_row(
            sheet_id=sheet_id,
            row_data=[now, "Commander", "Severity classified", "P0", "done"]
        )
        print(f"    Status: {row_result['status']}")
        print(f"    Result: {row_result['result']}")

    # Test timeline convenience
    print("\n[3] Testing create_timeline_sheet()...")
    timeline = create_timeline_sheet("TEST-003", "Redis Cache Failure", "P1")
    print(f"    Status:   {timeline['status']}")
    print(f"    Sheet ID: {timeline.get('sheet_id')}")

    return result["status"] == "ok"


def test_slack():
    """Test Slack tool."""
    hr("SLACK TOOL TEST")
    from tools.slack_tool import post_to_slack, post_rich_slack_message

    print("\n[1] Testing post_to_slack()...")
    result = post_to_slack("🧪 CrisisOps AI MCP test message — please ignore")
    print(f"    Result: {result}")

    print("\n[2] Testing post_rich_slack_message()...")
    result = post_rich_slack_message(
        incident_id="TEST-004",
        title="MCP Test — please ignore",
        severity="P2",
        triage_summary="This is an automated test of the Slack integration."
    )
    print(f"    Result: {result}")

    return "sent" in result.lower() or "not configured" in result.lower()


def test_calendar():
    """Test Calendar tool."""
    hr("GOOGLE CALENDAR MCP TEST")
    from tools.calendar_tool import create_war_room

    print("\n[1] Testing create_war_room() (P0)...")
    result = create_war_room(
        incident_id="TEST-005",
        title="MCP Test War Room — please ignore",
        severity="P0"
    )
    print(f"    Result: {result}")

    print("\n[2] Testing create_war_room() (P1 — should skip)...")
    result = create_war_room(
        incident_id="TEST-006",
        title="Should be skipped",
        severity="P1"
    )
    print(f"    Result: {result}")

    return True


# ── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_name = sys.argv[1] if len(sys.argv) > 1 else "all"

    tests = {
        "toolkit":  test_toolkit_status,
        "gmail":    test_gmail,
        "docs":     test_docs,
        "sheets":   test_sheets,
        "slack":    test_slack,
        "calendar": test_calendar,
    }

    print()
    print("🧪 CrisisOps AI — MCP Tools Test Suite")
    print(f"   Time: {datetime.utcnow().isoformat()}Z")

    if test_name == "all":
        results = {}
        for name, fn in tests.items():
            try:
                results[name] = fn()
            except Exception as e:
                print(f"\n  ❌ {name} FAILED: {e}")
                results[name] = False

        hr("RESULTS")
        for name, passed in results.items():
            icon = "✅" if passed else "❌"
            print(f"  {icon} {name}")
    else:
        if test_name in tests:
            try:
                tests[test_name]()
            except Exception as e:
                print(f"\n  ❌ FAILED: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"  Unknown test: {test_name}")
            print(f"  Available: {', '.join(tests.keys())}")
