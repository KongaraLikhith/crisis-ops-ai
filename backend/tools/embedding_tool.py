import os
from models import db, PastIncident
from google import genai

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = "gemini-embedding-001"
OUTPUT_DIMENSIONALITY = 768

def embed_text(text: str) -> list[float]:
    """
    Generate a 768-dimension embedding vector for a given text using Google Gemini embeddings.
    Returns a list of floats.
    """
    if not text:
        return []

    response = client.models.embed_content(
        model=MODEL,
        contents=text,
        config={
            "output_dimensionality": OUTPUT_DIMENSIONALITY
        },
    )

    if not response.embeddings:
        return []

    return response.embeddings[0].values

def embed_resolved_incident(past: PastIncident):
    """
    Accepts a PastIncident object, generates embedding from title + description + human_resolution,
    and stores it in the embedding column.
    """
    if not past:
        print("[WARN] No PastIncident provided")
        return

    text_to_embed = " ".join(filter(None, [
        past.title,
        past.description,
        past.human_resolution
    ]))

    past.embedding = embed_text(text_to_embed)
    db.session.commit()
    print(f"[INFO] Gemini embedding saved for incident {past.incident_id}")