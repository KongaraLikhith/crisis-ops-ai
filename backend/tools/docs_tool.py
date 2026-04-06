# backend/tools/docs_tool.py
# ── Google Docs MCP Tool ─────────────────────────────────────────────
# Creates and appends to Google Docs.
# Used by the Documentation Agent for incident tickets and post-mortems.
#
# Setup: run `python tools/google_auth.py` once to authorize.
# ─────────────────────────────────────────────────────────────────────
from tools.google_auth import get_google_creds


def create_doc(title, content):
    """
    Creates a new Google Doc with the given title and content.

    Args:
        title:   document title
        content: initial text content

    Returns:
        dict: {"status": "ok"/"error", "result": ..., "doc_id": ...}
    """
    creds = get_google_creds()

    if not creds:
        print(f"[Docs] FALLBACK — would create doc:")
        print(f"  Title: {title}")
        print(f"  Content: {content[:200]}...")
        return {
            "status": "ok",
            "result": f"Doc '{title}' logged to console (Docs not configured)",
            "doc_id": f"DEMO-DOC-{title[:10].replace(' ', '-').upper()}",
            "doc_url": None,
            "fallback": True
        }

    try:
        from googleapiclient.discovery import build

        # Create the document
        docs_service = build("docs", "v1", credentials=creds)
        doc = docs_service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]

        # Insert content if provided
        if content:
            requests = [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": content
                    }
                }
            ]
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests}
            ).execute()

        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        print(f"[Docs] Document created: {doc_url}")

        return {
            "status": "ok",
            "result": f"Document '{title}' created",
            "doc_id": doc_id,
            "doc_url": doc_url
        }

    except ImportError:
        print("[Docs] google-api-python-client not installed")
        return {"status": "error", "result": "Docs library not installed", "doc_id": None}
    except Exception as e:
        print(f"[Docs] Error creating document: {e}")
        return {"status": "error", "result": str(e), "doc_id": None}


def append_to_doc(doc_id, content):
    """
    Appends text content to the end of an existing Google Doc.

    Args:
        doc_id:  Google Doc ID
        content: text to append

    Returns:
        dict: {"status": "ok"/"error", "result": ...}
    """
    creds = get_google_creds()

    if not creds:
        print(f"[Docs] FALLBACK — would append to doc {doc_id}:")
        print(f"  Content: {content[:200]}...")
        return {
            "status": "ok",
            "result": f"Append logged to console (Docs not configured)",
            "fallback": True
        }

    try:
        from googleapiclient.discovery import build

        docs_service = build("docs", "v1", credentials=creds)

        # Get current document length to find end index
        doc = docs_service.documents().get(documentId=doc_id).execute()
        end_index = doc["body"]["content"][-1]["endIndex"] - 1

        requests = [
            {
                "insertText": {
                    "location": {"index": end_index},
                    "text": "\n\n" + content
                }
            }
        ]

        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests}
        ).execute()

        print(f"[Docs] Content appended to doc {doc_id}")
        return {"status": "ok", "result": f"Content appended to doc {doc_id}"}

    except ImportError:
        print("[Docs] google-api-python-client not installed")
        return {"status": "error", "result": "Docs library not installed"}
    except Exception as e:
        print(f"[Docs] Error appending to document: {e}")
        return {"status": "error", "result": str(e)}


def create_incident_doc(incident_id, title, severity, description=""):
    """
    Convenience: creates a formatted incident ticket document.
    """
    content = f"""INCIDENT TICKET
{'=' * 40}

Incident ID: {incident_id}
Title: {title}
Severity: {severity}
Status: Processing

Description:
{description or 'No description provided.'}

{'=' * 40}
AGENT ANALYSIS
(Results will be appended below as agents complete their work)

"""
    return create_doc(
        title=f"🚨 [{severity}] {title} — {incident_id}",
        content=content
    )


# ── CLI test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Google Docs MCP tool...")

    # Test create
    result = create_incident_doc(
        incident_id="TEST-001",
        title="Test Incident — please ignore",
        severity="P1",
        description="This is a test document from CrisisOps AI."
    )
    print(f"Create result: {result}")

    # Test append
    if result.get("doc_id"):
        append_result = append_to_doc(
            doc_id=result["doc_id"],
            content="POST-MORTEM\n\nThis incident was caused by a test."
        )
        print(f"Append result: {append_result}")
