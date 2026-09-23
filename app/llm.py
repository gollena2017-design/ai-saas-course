from dotenv import load_dotenv
import os
from typing import Any, Dict

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_client():
    try:
        from google import genai
    except Exception as e:
        raise RuntimeError("google-genai SDK is required. Install with 'pip install google-genai'") from e

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in environment")

    client = genai.Client(api_key=GEMINI_API_KEY)
    return client


def analyze_transactions_prompt(transactions: list[Dict[str, Any]]) -> str:
    # Build a compact prompt that asks for structured JSON output
    # The prompt instructs the model to output a JSON object with specific fields.
    return (
        "You are an AI assistant analyzing a user's financial transactions. "
        "Given the following transactions in JSON, return a JSON object with keys: "
        "summary (short string), categories (list of {name, total}), risks (list of strings), "
        "recommendations (list of strings). Do NOT invent transactions or amounts. "
        "Transactions: " + str(transactions)
    )


def call_gemini_analyze(transactions: list[Dict[str, Any]], model: str = "gemini-1.5-mini") -> Dict[str, Any]:
    client = get_client()

    prompt = analyze_transactions_prompt(transactions)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    text = getattr(response, "text", None) or str(response)

    # Return raw text; caller is responsible for validation/parsing
    return {
        "raw": text,
        "response_obj": response,
    }
