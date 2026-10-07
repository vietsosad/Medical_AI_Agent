import os

import google.generativeai as genai


google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise RuntimeError("Set GOOGLE_API_KEY before listing Gemini models.")

genai.configure(api_key=google_api_key)

try:
    for model in genai.list_models():
        if "generateContent" in model.supported_generation_methods:
            print(model.name)
except Exception as exc:
    print(f"Error: {exc}")
