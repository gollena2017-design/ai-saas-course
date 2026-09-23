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


def call_gemini_analyze(transactions: list[Dict[str, Any]], model: str = "gemini-3.6-flash") -> Dict[str, Any]:
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


def extract_json_from_text(text: str) -> Dict[str, Any] | None:
    """Try to extract a JSON object from free text. Returns parsed dict or None."""
    import json
    import re

    # find first { and last } to attempt to extract JSON block
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start:end+1]
    try:
        return json.loads(candidate)
    except Exception:
        # Try to clean common issues: single quotes -> double quotes
        candidate2 = candidate.replace("'", '"')
        try:
            return json.loads(candidate2)
        except Exception:
            # fallback: try regex to find simple key-value lists (not implemented)
            return None

