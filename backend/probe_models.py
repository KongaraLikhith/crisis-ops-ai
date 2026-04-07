import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# We prioritize Flash models as they are most likely to be free
candidate_models = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest"
]

print("Probing models for active quota...\n")

for model_name in candidate_models:
    print(f"Testing {model_name}...", end=" ", flush=True)
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("hi", generation_config={"max_output_tokens": 5})
        print("✅ SUCCESS")
        print(f"  Response: {response.text.strip()}")
    except Exception as e:
        if "429" in str(e):
            print("❌ QUOTA EXHAUSTED (429)")
        elif "404" in str(e) or "not found" in str(e).lower():
            print("❓ NOT FOUND")
        else:
            print(f"❌ ERROR: {str(e)[:50]}...")
    
    # Small delay to avoid accidental burst
    time.sleep(1)
