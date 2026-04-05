import os
from google import genai
from google.genai import types
from models import db, PastIncident
from sqlalchemy import or_, case
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


# ── EMBEDDING ────────────────────────────────────────────
def get_embedding(text_to_embed):
    """
    Generate 768-dim embedding using Gemini embedding model.
    """
    try:
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=[text_to_embed],
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"[ERROR] Embedding failed: {str(e)}")
        raise


# ── MAIN SEARCH ──────────────────────────────────────────
def search_similar_incidents(query_text, limit=3, return_mode="text"):
    """
    Search similar incidents using:
    1) Vector search (preferred)
    2) Keyword fallback

    return_mode:
      - "text" -> returns LLM-friendly formatted string
      - "json" -> returns list of dicts
    """
    try:
        query_vector = get_embedding(query_text)
        results = _vector_search(query_vector, limit=limit)
        if results:
            return _format_results(results, mode="vector", return_mode=return_mode)
    except Exception as e:
        print(f"[WARN] Vector search failed, using keyword fallback: {str(e)}")

    results = _keyword_search(query_text, limit=limit)
    if results:
        return _format_results(results, mode="keyword", return_mode=return_mode)

    if return_mode == "json":
        return []

    return "No similar past incidents found in history."


# ── VECTOR SEARCH ────────────────────────────────────────
def _vector_search(query_vector, limit=3):
    """
    Semantic search using pgvector cosine similarity.
    Prefer human_verified results first, then highest similarity.
    """
    rows = (
        db.session.query(
            PastIncident,
            (1 - PastIncident.embedding.cosine_distance(query_vector)).label("similarity")
        )
        .filter(PastIncident.embedding.isnot(None))
        .order_by(
            case(
                (PastIncident.resolution_confidence == "human_verified", 0),
                else_=1
            ),
            (1 - PastIncident.embedding.cosine_distance(query_vector)).desc()
        )
        .limit(limit)
        .all()
    )

    return rows


# ── KEYWORD FALLBACK ─────────────────────────────────────
def _keyword_search(query_text, limit=3):
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'and', 'or',
        'for', 'in', 'on', 'at', 'to', 'all', 'not', 'no',
        'with', 'from', 'that', 'this', 'into', 'after',
        'before', 'during', 'while', 'users', 'unable'
    }

    words = [
        w.lower().strip(".,:;!?()[]{}")
        for w in query_text.split()
        if w.lower() not in stop_words and len(w) > 3
    ]

    if not words:
        return []

    filters = []
    for word in words[:6]:
        like = f"%{word}%"
        filters.extend([
            PastIncident.title.ilike(like),
            PastIncident.description.ilike(like),
            PastIncident.category.ilike(like),
            PastIncident.human_root_cause.ilike(like),
            PastIncident.agent_root_cause.ilike(like),
            PastIncident.human_resolution.ilike(like),
            PastIncident.agent_resolution.ilike(like),
        ])

    rows = (
        db.session.query(PastIncident, db.literal(0.0).label("similarity"))
        .filter(or_(*filters))
        .order_by(
            case(
                (PastIncident.resolution_confidence == "human_verified", 0),
                else_=1
            ),
            PastIncident.created_at.desc()
        )
        .limit(limit)
        .all()
    )

    return rows


# ── FORMAT RESULTS ───────────────────────────────────────
def _format_results(rows, mode="vector", return_mode="text"):
    formatted = []

    for row, score in rows:
        best_root = row.human_root_cause or row.agent_root_cause or "Unknown"
        best_fix = row.human_resolution or row.agent_resolution or "Unknown"

        if row.resolution_confidence == "human_verified":
            confidence = "Human verified"
        elif row.human_root_cause or row.human_resolution:
            confidence = "Human corrected"
        else:
            confidence = "Agent suggestion only"

        item = {
            "title": row.title,
            "description": row.description,
            "category": row.category,
            "severity": row.severity,
            "root_cause": best_root,
            "resolution": best_fix,
            "confidence": confidence,
            "similarity_score": round(float(score), 4) if score is not None else None,
        }
        formatted.append(item)

    if return_mode == "json":
        return formatted

    header = (
        "SIMILAR PAST INCIDENTS (semantic search):\n\n"
        if mode == "vector"
        else "SIMILAR PAST INCIDENTS (keyword fallback):\n\n"
    )

    output = header
    for i, item in enumerate(formatted, start=1):
        output += f"{i}. Title: {item['title']}\n"
        output += f"   Category: {item['category'] or 'uncategorized'}\n"
        output += f"   Severity: {item['severity'] or 'Unknown'}\n"
        output += f"   Root cause: {item['root_cause']}\n"
        output += f"   Resolution: {item['resolution']}\n"
        output += f"   Confidence: {item['confidence']}\n"
        if item["similarity_score"] is not None:
            output += f"   Similarity Score: {item['similarity_score']}\n"
        output += "\n"

    return output.strip()