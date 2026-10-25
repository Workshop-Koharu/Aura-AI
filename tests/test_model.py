import torch

from aura.model import AuraTransformer
from aura.train import DEFAULT_CONFIG


def test_model_shape_and_parameter_budget():
    model = AuraTransformer(DEFAULT_CONFIG)
    assert sum(p.numel() for p in model.parameters()) > 4_500_000
    x = torch.randint(0, DEFAULT_CONFIG["vocab_size"], (2, 32))
    logits, loss = model(x, x)
    assert logits.shape == (2, 32, DEFAULT_CONFIG["vocab_size"])
    assert loss is not None and torch.isfinite(loss)


def test_attention_is_causal():
    torch.manual_seed(7)
    model = AuraTransformer(DEFAULT_CONFIG).eval()
    a = torch.randint(0, DEFAULT_CONFIG["vocab_size"], (1, 12))
    b = a.clone()
    b[0, -1] = (b[0, -1] + 1) % DEFAULT_CONFIG["vocab_size"]
    with torch.inference_mode():
        la, _ = model(a)
        lb, _ = model(b)
    assert torch.allclose(la[:, :-1], lb[:, :-1], atol=1e-5, rtol=1e-5)


def test_generation_only_samples_trained_byte_ids():
    torch.manual_seed(3)
    model = AuraTransformer(DEFAULT_CONFIG).eval()
    prompt = torch.randint(0, 256, (1, 8))
    with torch.inference_mode():
        generated = model.generate(prompt, max_new_tokens=12, temperature=0.8, top_k=40)
    new_tokens = generated[:, prompt.shape[1] :]
    assert new_tokens.shape[1] == 12
    assert torch.all(new_tokens < 256)
