import asyncio
import json

from app import api
from app.api import AIAnalyzeRequest


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


async def main():
    api.call_gemini_analyze = fake_call
    req = AIAnalyzeRequest(limit=5)
    res = await api.analyze_transactions_endpoint(req)
    print(res)


if __name__ == '__main__':
    asyncio.run(main())
