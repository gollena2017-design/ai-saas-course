import json
import asyncio

from fastapi.testclient import TestClient

from app.api import app
from app.db import async_session
from app.models import ChatThread


def test_chat_endpoint_creates_thread_and_checkpoint(monkeypatch):
    # Fake LLM reply
    def fake_call(transactions, model='gemini-3.6-flash', **kwargs):
        return {"raw": "{\"reply\": \"Hello from LLM\"}", "response_obj": None, "model_used": model, "attempts": 1}

    monkeypatch.setattr('app.api.call_gemini_analyze', fake_call)

    client = TestClient(app)

    resp = client.post('/api/ai/chat', json={"message": "Привіт"})
    assert resp.status_code == 200
    body = resp.json()
    assert 'thread_id' in body and body['thread_id'] is not None
    assert 'answer' in body

    thread_id = body['thread_id']
    # checkpoint is returned in response
    assert 'checkpoint' in body
    data = body['checkpoint']
    assert data.get('last_user') == 'Привіт'
    assert 'Hello from LLM' in (data.get('last_assistant') or '')
