# backend/backfill_embeddings.py
# Run manually:
# python backfill_embeddings.py

## to be tested. [06-04-2026]

from datetime import datetime
from main import app
from models import db, PastIncident
from tools.search_tool import get_embedding


def build_embedding_text(row: PastIncident) -> str:
    """
    Build a rich text blob for embedding so semantic search has useful context.
    Prefer human truth where available, but also include agent output.
    """
    parts = [
        f"Title: {row.title or ''}",
        f"Description: {row.description or ''}",
        f"Category: {row.category or ''}",
        f"Severity: {row.severity or ''}",
        f"Agent Root Cause: {row.agent_root_cause or ''}",
        f"Agent Resolution: {row.agent_resolution or ''}",
        f"Human Root Cause: {row.human_root_cause or ''}",
        f"Human Resolution: {row.human_resolution or ''}",
        f"Agent Comms: {row.agent_comms or ''}",
        f"Agent Postmortem: {row.agent_postmortem or ''}",
        f"Resolution Confidence: {row.resolution_confidence or ''}",
    ]
    return "\n".join(parts).strip()


def backfill_embeddings(only_missing=True, dry_run=False):
    """
    Backfill embeddings for past_incidents.

    Args:
        only_missing (bool): If True, only rows with NULL embedding are updated.
        dry_run (bool): If True, no DB updates are committed.
    """
    query = PastIncident.query.order_by(PastIncident.id.asc())

    if only_missing:
        query = query.filter(PastIncident.embedding.is_(None))

    rows = query.all()

    if not rows:
        print("No past_incidents found to backfill.")
        return

    print(f"Found {len(rows)} past_incident rows to process.")

    updated = 0
    failed = 0

    for row in rows:
        try:
            text_to_embed = build_embedding_text(row)

            if not text_to_embed.strip():
                print(f"[SKIP] id={row.id} | empty text")
                continue

            embedding = get_embedding(text_to_embed)

            if dry_run:
                print(f"[DRY RUN] Would update id={row.id} | title={row.title}")
            else:
                row.embedding = embedding
                row.updated_at = datetime.utcnow()
                db.session.add(row)
                db.session.commit()
                print(f"[OK] Updated id={row.id} | title={row.title}")

            updated += 1

        except Exception as e:
            db.session.rollback()
            failed += 1
            print(f"[ERROR] Failed id={row.id} | title={row.title} | error={str(e)}")

    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"Updated: {updated}")
    print(f"Failed : {failed}")
    print(f"Only Missing Mode: {only_missing}")
    print(f"Dry Run: {dry_run}")


if __name__ == "__main__":
    with app.app_context():
        # Default: update only rows where embedding is NULL
        backfill_embeddings(only_missing=True, dry_run=False)