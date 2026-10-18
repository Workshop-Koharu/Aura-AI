import torch

from aura.model import AuraTransformer
from aura.tokenizer import ByteTokenizer


def test_transformer_logits_and_loss_shapes() -> None:
    config = {
        "vocab_size": ByteTokenizer.VOCAB_SIZE,
        "block_size": 16,
        "n_embd": 32,
        "n_head": 4,
        "n_layer": 2,
        "dropout": 0.0,
    }
    model = AuraTransformer(config)
    tokens = torch.randint(0, ByteTokenizer.VOCAB_SIZE, (2, 12))
    logits, loss = model(tokens, tokens)
    assert logits.shape == (2, 12, ByteTokenizer.VOCAB_SIZE)
    assert loss is not None and torch.isfinite(loss)


def test_transformer_rejects_long_context() -> None:
    config = {
        "vocab_size": ByteTokenizer.VOCAB_SIZE,
        "block_size": 8,
        "n_embd": 16,
        "n_head": 4,
        "n_layer": 1,
        "dropout": 0.0,
    }
    model = AuraTransformer(config)
    try:
        model(torch.zeros((1, 9), dtype=torch.long))
    except ValueError as exc:
        assert "block_size" in str(exc)
    else:
        raise AssertionError("Expected context length validation")
