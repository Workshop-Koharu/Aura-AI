from fastapi.testclient import TestClient

from app.main import app
from app.settings import settings

client = TestClient(app)


def test_chat_requires_model_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "model_api_key", "")
    response = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 503
    assert "AURA_MODEL_API_KEY" in response.json()["detail"]


def test_chat_rejects_empty_messages() -> None:
    response = client.post("/v1/chat", json={"messages": []})
    assert response.status_code == 422
