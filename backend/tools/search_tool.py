# backend/tools/search_tool.py
import os
from google import genai
from google.genai import types 
from models import db, PastIncident
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

# Initialize the Gemini Client 
# We remove http_options to let it default to v1beta, which supports the new model
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def get_embedding(text_to_embed):
    """
    Uses gemini-embedding-001 on the v1beta endpoint.
    Truncates the native 3072 dimensions to 768 to fit your DB schema.
    """
    try:
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=[text_to_embed],
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"Embedding failed: {e}")
        raise e

def search_similar_incidents(query, limit=3):
    """Performs a Cosine Similarity search in Cloud SQL."""
    query_vector = get_embedding(query)
    
    results = db.session.query(
        PastIncident,
        (1 - PastIncident.embedding.cosine_distance(query_vector)).label("similarity")
    ).order_by(text("similarity DESC")).limit(limit).all()

    formatted_results = []
    for row, score in results:
        data = row.to_dict()
        data["similarity_score"] = round(float(score), 4)
        formatted_results.append(data)
    
    return formatted_results