import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

MODELS = [
    "models/gemini-1.5-flash-latest",
    "models/gemini-1.5-flash",
    "models/gemini-1.5-flash-8b",
    "models/gemini-2.0-flash-lite",
    "models/gemini-2.0-flash-exp",
    "models/gemini-2.5-flash",
    "models/gemini-3.1-flash-lite-preview"
]

for m in MODELS:
    print(f"Testing {m}...")
    try:
        # Use the name without prefix if it fails with prefix, or vice versa
        response = client.models.generate_content(
            model=m,
            contents="hi"
        )
        print(f"  {m}: SUCCESS")
    except Exception as e:
        print(f"  {m}: FAILED - {e}")
