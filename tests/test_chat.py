from fastapi.testclient import TestClient

from app.main import app
from aura.tokenizer import ByteTokenizer

client = TestClient(app)


def test_chat_returns_clear_not_trained_status(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AURA_CHECKPOINT_PATH", str(tmp_path / "missing.pt"))
    response = client.post("/v1/chat", json={"messages": [{"role": "user", "content": "안녕"}]})
    assert response.status_code == 503
    assert "자체 모델" in response.json()["detail"]


def test_chat_rejects_empty_messages() -> None:
    assert client.post("/v1/chat", json={"messages": []}).status_code == 422


def test_tokenizer_round_trip_korean_and_english() -> None:
    tokenizer = ByteTokenizer()
    text = "안녕하세요 Aura AI"
    assert tokenizer.decode(tokenizer.encode(text)) == text


def test_tokenizer_special_tokens() -> None:
    assert ByteTokenizer().encode("A", add_bos=True, add_eos=True) == [257, 65, 256]
