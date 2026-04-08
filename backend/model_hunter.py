import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

print("Starting model hunt...\n")

working_models = []

for m in client.models.list():
    if "generateContent" not in m.supported_actions:
        continue

    model_name = m.name
    print(f"Testing {model_name}...", end=" ", flush=True)
    try:
        resp = client.models.generate_content(
            model=model_name,
            contents="hi",
        )
        print("✅ SUCCESS")
        working_models.append(model_name)
    except Exception as e:
        text = str(e)
        if "429" in text or "RESOURCE_EXHAUSTED" in text:
            print("❌ 429 QUOTA")
        elif "404" in text or "NOT_FOUND" in text:
            print("❌ 404 NOT FOUND")
        else:
            print(f"❌ ERROR: {text[:60]}...")
    time.sleep(1)

print("\n--- RESULTS ---")
for wm in working_models:
    print(" -", wm)