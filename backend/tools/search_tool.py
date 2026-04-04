# backend/tools/search_tool.py
from models import PastIncident

def search_similar_incidents(query_text):
    """
    Keyword search using SQLAlchemy ORM — no raw SQL needed.
    Prefers human_verified results over agent_only.
    Falls back gracefully if DB is empty.
    """
    stop_words = {
        'the','a','an','is','are','was','and','or',
        'for','in','on','at','to','all','not','no'
    }
    words = [
        w.lower() for w in query_text.split()
        if w.lower() not in stop_words and len(w) > 3
    ]

    if not words:
        return "No similar past incidents found."

    # Build OR filter across title and root cause columns
    from sqlalchemy import or_
    filters = []
    for word in words[:5]:
        like = f"%{word}%"
        filters.append(PastIncident.title.ilike(like))
        filters.append(PastIncident.human_root_cause.ilike(like))
        filters.append(PastIncident.agent_root_cause.ilike(like))

    results = PastIncident.query \
        .filter(or_(*filters)) \
        .order_by(
            # human_verified ranked first
            PastIncident.resolution_confidence.desc(),
            PastIncident.created_at.desc()
        ) \
        .limit(3).all()

    if not results:
        return "No similar past incidents found in history."

    output = "SIMILAR PAST INCIDENTS:\n\n"
    for r in results:
        best_root = r.human_root_cause or r.agent_root_cause
        best_fix  = r.human_resolution or r.agent_resolution
        verified  = "Human verified" if r.agent_was_correct else \
                    ("Human corrected" if r.human_root_cause else "Agent suggestion only")
        output += f"Title: {r.title}\n"
        output += f"Root cause: {best_root}\n"
        output += f"Resolution: {best_fix}\n"
        output += f"Confidence: {verified}\n\n"
    return output