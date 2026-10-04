import json
from fastapi.testclient import TestClient

from app import api


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


def main():
    api.call_gemini_analyze = fake_call
    client = TestClient(api.app)
    resp = client.post('/api/ai/analyze-transactions', json={'limit': 5})
    print('status', resp.status_code)
    try:
        print('json:', resp.json())
    except Exception:
        print('text:', resp.text)


if __name__ == '__main__':
    main()
