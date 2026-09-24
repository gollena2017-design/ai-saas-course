import json
import pytest

from fastapi.testclient import TestClient

from app.api import app


def test_ai_endpoint_with_mock(monkeypatch):
    # Mock call_gemini_analyze to avoid real external calls
    def fake_call(transactions, model='gemini-3.6-flash', **kwargs):
        return {
            'raw': json.dumps({
                'summary': 'Тестовий підсумок',
                'categories': [{'name': 'Тест', 'total': 100.0}],
                'risks': [],
                'recommendations': [],
            }),
            'response_obj': None,
            'model_used': model,
            'attempts': 1,
        }

    monkeypatch.setattr('app.api.call_gemini_analyze', fake_call)

    # Create TestClient after monkeypatch so the test server uses the mock
    client = TestClient(app)

    resp = client.post('/api/ai/analyze-transactions', json={'limit': 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is True
    assert 'llm' in body
    assert body['llm']['parsed']['summary'] == 'Тестовий підсумок'
