import os

from google import genai
from google.genai import types

from models import db, PastIncident

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = "gemini-embedding-001"
OUTPUT_DIMENSIONALITY = 768

client = genai.Client(api_key=API_KEY) if API_KEY else None


def embed_text(text: str) -> list[float]:
    """
    Generate a 768-dimension embedding vector for text using Gemini embeddings.
    Returns a list of floats.
    """
    if not text or not text.strip():
        return []

    if client is None:
        print("[WARN] GOOGLE_API_KEY not set; skipping embedding generation")
        return []

    try:
        response = client.models.embed_content(
            model=MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=OUTPUT_DIMENSIONALITY,
            ),
        )

        if not response.embeddings:
            return []

        return response.embeddings[0].values

    except Exception as e:
        print(f"[ERROR] Failed to generate embedding: {e}")
        return []


def embed_resolved_incident(past: PastIncident):
    """
    Generate an embedding from title + description + human_resolution
    and store it in the PastIncident.embedding column.
    """
    if not past:
        print("[WARN] No PastIncident provided")
        return

    text_to_embed = " ".join(
        filter(
            None,
            [
                past.title,
                past.description,
                past.human_resolution,
            ],
        )
    ).strip()

    if not text_to_embed:
        print(f"[WARN] No text available to embed for incident {past.incident_id}")
        return

    embedding = embed_text(text_to_embed)
    if not embedding:
        print(f"[WARN] Embedding generation returned empty for incident {past.incident_id}")
        return

    past.embedding = embedding
    db.session.commit()
    print(f"[INFO] Gemini embedding saved for incident {past.incident_id}")
