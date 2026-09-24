import asyncio
import json
from fastapi.testclient import TestClient
from app.api import app


def test_parallel_chat_requests(monkeypatch):
    # Mock LLM to respond quickly
    def fake_call(payload, model='gemini-3.6-flash', **kwargs):
        return {"raw": json.dumps({"reply": "ok"})}

    monkeypatch.setattr('app.api.call_gemini_analyze', fake_call)

    client = TestClient(app)

    async def send():
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: client.post('/api/ai/chat', json={"message": "hi"}))

    # Run a batch of parallel requests that previously caused InterfaceError
    async def run_batch(n=8):
        tasks = [asyncio.create_task(send()) for _ in range(n)]
        results = await asyncio.gather(*tasks)
        return results

    results = asyncio.run(run_batch(8))
    for r in results:
        assert r.status_code == 200
