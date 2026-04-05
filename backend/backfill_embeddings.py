from datetime import datetime
from main import app
from models import db, PastIncident
from tools.search_tool import get_embedding


def build_embedding_text(row: PastIncident) -> str:
    """
    Build clean, high-signal embedding text.
    Focus only on relevant semantic fields.
    """
    return "\n".join([
        f"Title: {row.title or ''}",
        f"Description: {row.description or ''}",
        f"Category: {row.category or ''}",
        f"Severity: {row.severity or ''}",
        f"Root Cause: {row.human_root_cause or row.agent_root_cause or ''}",
        f"Resolution: {row.human_resolution or row.agent_resolution or ''}",
    ]).strip()


def backfill_embeddings(only_missing=True, dry_run=False):
    query = PastIncident.query.order_by(PastIncident.id.asc())

    if only_missing:
        query = query.filter(PastIncident.embedding.is_(None))

    rows = query.all()

    if not rows:
        print("No past_incidents found to backfill.")
        return

    print(f"Found {len(rows)} rows to process.")

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
                print(f"[DRY RUN] Would update id={row.id}")
            else:
                row.embedding = embedding
                row.updated_at = datetime.utcnow()
                db.session.add(row)
                db.session.commit()
                print(f"[OK] Updated id={row.id}")

            updated += 1

        except Exception as e:
            db.session.rollback()
            failed += 1
            print(f"[ERROR] id={row.id} | {str(e)}")

    print("\n" + "=" * 50)
    print("BACKFILL COMPLETE")
    print("=" * 50)
    print(f"Updated: {updated}")
    print(f"Failed : {failed}")


if __name__ == "__main__":
    with app.app_context():
        backfill_embeddings(only_missing=True, dry_run=False)