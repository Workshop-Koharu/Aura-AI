import torch
from fastapi.testclient import TestClient
from aura.tokenizer import AuraTokenizer, BOS, EOS
from aura.models.transformer import AuraModel
from aura.config import ModelConfig
from api.main import app

client = TestClient(app)

def test_tokenizer_roundtrip():
    samples = ["안녕하세요 Aura", "Python is useful.", "이미지와 음성"]
    tokenizer = AuraTokenizer.train(samples, max_merges=128, min_frequency=2)
    for text in samples:
        ids = tokenizer.encode(text)
        assert ids[0] == BOS and ids[-1] == EOS
        assert tokenizer.decode(ids) == text

def test_model_text_forward():
    cfg = ModelConfig(vocab_size=300, d_model=64, n_layers=2, n_heads=4, d_ff=128,
                      max_seq_len=32, image_size=32, image_patch=8,
                      image_width=64, image_layers=1, audio_width=64, audio_layers=1)
    model = AuraModel(cfg)
    ids = torch.randint(0, 300, (1, 12))
    logits, loss = model(ids, labels=ids)
    assert logits.shape == (1, 12, 300)
    assert torch.isfinite(loss)

def test_model_image_and_audio_forward():
    cfg = ModelConfig(vocab_size=300, d_model=64, n_layers=2, n_heads=4, d_ff=128,
                      max_seq_len=32, image_size=32, image_patch=8,
                      image_width=64, image_layers=1, audio_width=64, audio_layers=1)
    model = AuraModel(cfg)
    ids = torch.randint(0, 300, (1, 8))
    image = torch.randn(1, 3, 32, 32)
    audio = torch.randn(1, 1, 80, 64)
    logits, loss = model(ids, image=image, audio=audio, labels=ids)
    assert logits.shape == (1, 10, 300)
    assert torch.isfinite(loss)

def test_local_api_reports_untrained_model():
    health = client.get("/api/health")
    status = client.get("/api/model/status")
    assert health.status_code == 200
    assert health.json()["engine"] == "aura-from-scratch"
    assert status.status_code == 200
    assert status.json()["checkpoint_exists"] is False
    assert status.json()["model_parameters"] == 47895456

def test_chat_refuses_to_claim_untrained_ability():
    response = client.post("/api/chat", json={"message": "안녕"})
    assert response.status_code == 503
