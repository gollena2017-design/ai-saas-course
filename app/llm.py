from dotenv import load_dotenv
import os
import time
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
        "Return only a single JSON object. Transactions: " + str(transactions)
    )


def call_gemini_analyze(
    transactions: list[Dict[str, Any]],
    model: str = "gemini-3.6-flash",
    max_retries: int = 3,
    backoff_factor: float = 1.0,
) -> Dict[str, Any]:
    """Call Gemini with retries and a simple fallback model on repeated failures.

    Returns a dict with keys: raw, response_obj, model_used, attempts
    """
    client = get_client()
    prompt = analyze_transactions_prompt(transactions)

    models_to_try = [model, "gemini-3.5-mini"]

    last_exc = None
    attempts = 0
    for m in models_to_try:
        attempts = 0
        for attempt in range(1, max_retries + 1):
            attempts = attempt
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=prompt,
                )

                text = getattr(response, "text", None) or str(response)
                return {
                    "raw": text,
                    "response_obj": response,
                    "model_used": m,
                    "attempts": attempts,
                }
            except Exception as e:
                # If service unavailable, sleep and retry (exponential backoff)
                last_exc = e
                wait = backoff_factor * (2 ** (attempt - 1))
                time.sleep(wait)
                continue

    # all attempts failed
    return {
        "raw": None,
        "response_obj": None,
        "model_used": models_to_try[-1],
        "attempts": attempts,
        "error": str(last_exc),
    }


def extract_json_from_text(text: str) -> Dict[str, Any] | None:
    """Try to extract a JSON object from free text. Returns parsed dict or None."""
    import json
    import re

    if not text:
        return None

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

