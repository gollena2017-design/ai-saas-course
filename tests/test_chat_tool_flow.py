import json

from fastapi.testclient import TestClient

from app.api import app


def test_tool_call_flow(monkeypatch):
    # First mock: LLM returns a tool call request
    def fake_call_first(transactions, model='gemini-3.6-flash', **kwargs):
        return {"raw": json.dumps({"tool_call": {"name": "get_top_expenses", "args": {"limit": 2}}})}

    # Second mock: LLM final reply after tool result
    def fake_call_second(transactions, model='gemini-3.6-flash', **kwargs):
        return {"raw": json.dumps({"reply": "Ось ваші топ витрати."})}

    # Monkeypatch call_gemini_analyze to return first then second
    calls = {"n": 0}

    def dispatcher(transactions, model='gemini-3.6-flash', **kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            return fake_call_first(transactions, model=model)
        return fake_call_second(transactions, model=model)

    monkeypatch.setattr('app.api.call_gemini_analyze', dispatcher)

    client = TestClient(app)
    resp = client.post('/api/ai/chat', json={"message": "Покажи топ витрат"})
    assert resp.status_code == 200
    body = resp.json()
    assert 'answer' in body
    ans = body['answer']
    try:
        parsed = json.loads(ans)
        assert 'reply' in parsed and 'Ось ваші топ витрати' in parsed['reply']
    except Exception:
        assert 'Ось ваші топ витрати' in ans
