# backend/agents/docs_agent.py
# ── Documentation Agent ──────────────────────────────────────────────
# Handles all documentation when an incident is triggered:
#   1. Generates a post-mortem draft via LLM
#   2. Creates a Google Doc incident ticket
#   3. Creates a Google Sheet timeline and logs agent actions
# ─────────────────────────────────────────────────────────────────────
from datetime import datetime
from agents.base import get_llm
from tools.db_tools import log_action
from tools.docs_tool import create_incident_doc, append_to_doc
from tools.sheets_tool import create_timeline_sheet, append_row


async def run_docs(incident_id, title, severity):
    llm = get_llm()

    # ── 1. Generate post-mortem draft via LLM ────────────────
    prompt = f"""You are a technical writer who creates incident post-mortems.

Incident: {title}
Severity: {severity}
Incident ID: {incident_id}

Write a professional post-mortem document with these sections:
# Post-Mortem: [title]

## Summary
[2-3 sentence summary of what happened]

## Root Cause
[Technical analysis of the likely root cause]

## Timeline
[Estimated timeline with timestamps]

## Impact
[Who and what was affected]

## Action Items
[3-5 numbered action items to prevent recurrence]

Be realistic and technical. This is an auto-generated draft that will be
reviewed and refined by the human responder."""

    result = llm.invoke(prompt)
    postmortem = result.content.strip()
    log_action(incident_id, "Docs", "Post-mortem drafted", postmortem[:150])

    # ── 2. Create Google Doc incident ticket ─────────────────
    doc_result = create_incident_doc(
        incident_id=incident_id,
        title=title,
        severity=severity,
        description=f"Auto-generated incident ticket.\n\nPost-Mortem Draft:\n{postmortem}"
    )
    doc_id = doc_result.get("doc_id")
    doc_url = doc_result.get("doc_url", "")

    if doc_url:
        log_action(incident_id, "Docs", "Incident doc created", doc_url)
    else:
        log_action(incident_id, "Docs", "Incident doc created",
                   doc_result.get("result", "created"))

    # ── 3. Create Google Sheet timeline ──────────────────────
    sheet_result = create_timeline_sheet(
        incident_id=incident_id,
        title=title,
        severity=severity
    )
    sheet_id = sheet_result.get("sheet_id")
    sheet_url = sheet_result.get("sheet_url", "")

    if sheet_url:
        log_action(incident_id, "Docs", "Timeline sheet created", sheet_url)
    else:
        log_action(incident_id, "Docs", "Timeline sheet created",
                   sheet_result.get("result", "created"))

    # ── 4. Log initial timeline events ───────────────────────
    now = datetime.utcnow().isoformat()
    if sheet_id:
        # Log the incident creation event
        append_row(sheet_id, [
            now, "Commander", "Incident triggered", title, "processing"
        ])
        # Log severity classification
        append_row(sheet_id, [
            now, "Commander", "Severity classified", severity, "done"
        ])
        # Log doc creation
        append_row(sheet_id, [
            now, "Docs", "Post-mortem drafted", "Auto-generated", "done"
        ])

    return postmortem
