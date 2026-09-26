import json

from fastapi.testclient import TestClient

from app.api import app


def test_chat_creates_pending_action_and_cancel_does_not_execute(monkeypatch):
    """The chat may propose an action, but only the confirm endpoint can execute it."""
    def fake_llm(_payload, **_kwargs):
        return {
            "raw": json.dumps({
                "action_proposal": {
                    "action_type": "create_transaction",
                    "payload": {
                        "type": "expense",
                        "amount": 451,
                        "category": "Тестова категорія",
                        "description": "скасована дія",
                        "date": "2026-09-26",
                    },
                    "reply": "Підтвердьте дію.",
                }
            })
        }

    monkeypatch.setattr("app.api.call_gemini_analyze", fake_llm)
    client = TestClient(app)

    chat_response = client.post("/api/ai/chat", json={"message": "Додай витрату"})
    assert chat_response.status_code == 200
    action = chat_response.json()["pending_action"]
    assert action["status"] == "pending"
    assert action["payload"]["amount"] == "451"

    cancel_response = client.post(f"/api/ai/actions/{action['action_id']}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["action"]["status"] == "cancelled"

    # A cancelled action cannot be executed later.
    confirm_response = client.post(f"/api/ai/actions/{action['action_id']}/confirm")
    assert confirm_response.status_code == 409
