import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

print("Starting Exhaustive Model Hunt...\n")

working_models = []

for m in genai.list_models():
    if 'generateContent' not in m.supported_generation_methods:
        continue
        
    model_name = m.name
    print(f"Testing {model_name}...", end=" ", flush=True)
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("hi", generation_config={"max_output_tokens": 5})
        print("✅ SUCCESS")
        working_models.append(model_name)
    except Exception as e:
        if "429" in str(e):
            print("❌ 429 QUOTA")
        else:
            print(f"❌ ERROR: {str(e)[:40]}...")
    
    time.sleep(1)

print("\n--- RESULTS ---")
print("Working Models:")
for wm in working_models:
    print(f" - {wm}")
