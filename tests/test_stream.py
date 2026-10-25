from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chat_stream_emits_progress_and_complete(monkeypatch) -> None:
    monkeypatch.setattr("app.main.model_ready", lambda: True)
    monkeypatch.setattr("app.main._reply", lambda messages: "테스트 답변입니다.")
    response = client.post(
        "/v1/chat/stream",
        json={"messages": [{"role": "user", "content": "테스트 질문"}]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: progress\ndata: {"stage": "received", "message": "요청을 확인했어요."}' in response.text
    assert 'event: progress\ndata: {"stage": "generating", "message": "자체 Transformer가 답변을 생성하고 있어요."}' in response.text
    assert 'event: complete\ndata: {"reply": "테스트 답변입니다.", "message": "답변 생성이 완료됐어요."}' in response.text


def test_chat_stream_rejects_missing_checkpoint(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.main.model_ready", lambda: False)
    response = client.post(
        "/v1/chat/stream",
        json={"messages": [{"role": "user", "content": "테스트 질문"}]},
    )
    assert response.status_code == 503
