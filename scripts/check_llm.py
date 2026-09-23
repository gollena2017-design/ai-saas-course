from dotenv import load_dotenv
import os
import sys

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print("GEMINI_API_KEY present:", bool(GEMINI_API_KEY))

if not GEMINI_API_KEY:
    print("GEMINI_API_KEY is not set. Please add it to .env and retry.")
    sys.exit(2)

try:
    from app.llm import get_client
except Exception as e:
    print("Failed to import app.llm:", e)
    sys.exit(3)

try:
    client = get_client()
    print("Client created")
except Exception as e:
    print("Error creating client:", e)
    sys.exit(4)

try:
    print("Sending test prompt to Gemini...")
    resp = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Відповідай одним реченням: Gemini API працює?",
    )
    text = getattr(resp, "text", None) or str(resp)
    print("-- Gemini response start --")
    print(text)
    print("-- Gemini response end --")
except Exception as e:
    print("LLM request failed:", e)
    sys.exit(5)

print("LLM smoke test completed successfully.")
