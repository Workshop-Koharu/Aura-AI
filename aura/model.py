from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class CausalSelfAttention(nn.Module):
    def __init__(self, n_embd: int, n_head: int, block_size: int, dropout: float) -> None:
        super().__init__()
        if n_embd % n_head:
            raise ValueError("n_embd must be divisible by n_head")
        self.n_head, self.head_dim = n_head, n_embd // n_head
        self.qkv = nn.Linear(n_embd, 3 * n_embd, bias=False)
        self.proj = nn.Linear(n_embd, n_embd, bias=False)
        self.attn_dropout, self.resid_dropout = nn.Dropout(dropout), nn.Dropout(dropout)
        self.register_buffer(
            "causal_mask", torch.tril(torch.ones(block_size, block_size, dtype=torch.bool))
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, length, channels = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        q = q.view(batch, length, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(batch, length, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(batch, length, self.n_head, self.head_dim).transpose(1, 2)
        scores = (q @ k.transpose(-2, -1)) * (self.head_dim**-0.5)
        scores = scores.masked_fill(~self.causal_mask[:length, :length], float("-inf"))
        weights = self.attn_dropout(F.softmax(scores, dim=-1))
        result = (weights @ v).transpose(1, 2).contiguous().view(batch, length, channels)
        return self.resid_dropout(self.proj(result))


class TransformerBlock(nn.Module):
    def __init__(self, config: dict[str, int | float]) -> None:
        super().__init__()
        width = int(config["n_embd"])
        self.ln1 = nn.LayerNorm(width)
        self.attn = CausalSelfAttention(
            width, int(config["n_head"]), int(config["block_size"]), float(config["dropout"])
        )
        self.ln2 = nn.LayerNorm(width)
        self.mlp = nn.Sequential(
            nn.Linear(width, 4 * width),
            nn.GELU(),
            nn.Linear(4 * width, width),
            nn.Dropout(float(config["dropout"])),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        return x + self.mlp(self.ln2(x))


class AuraTransformer(nn.Module):
    """Decoder-only Transformer with random initialization and next-token prediction."""

    def __init__(self, config: dict[str, int | float]) -> None:
        super().__init__()
        self.config = dict(config)
        width = int(config["n_embd"])
        self.token_embedding = nn.Embedding(int(config["vocab_size"]), width)
        self.position_embedding = nn.Embedding(int(config["block_size"]), width)
        self.dropout = nn.Dropout(float(config["dropout"]))
        self.blocks = nn.Sequential(
            *(TransformerBlock(config) for _ in range(int(config["n_layer"])))
        )
        self.final_norm = nn.LayerNorm(width)
        self.lm_head = nn.Linear(width, int(config["vocab_size"]), bias=False)
        self.lm_head.weight = self.token_embedding.weight
        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self, input_ids: torch.Tensor, targets: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        _, length = input_ids.shape
        if length > int(self.config["block_size"]):
            raise ValueError("Input sequence exceeds block_size")
        positions = torch.arange(length, device=input_ids.device)
        x = self.dropout(self.token_embedding(input_ids) + self.position_embedding(positions))
        logits = self.lm_head(self.final_norm(self.blocks(x)))
        loss = (
            F.cross_entropy(logits.reshape(-1, logits.size(-1)), targets.reshape(-1))
            if targets is not None
            else None
        )
        return logits, loss

    @torch.no_grad()
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int,
        temperature: float = 0.8,
        top_k: int = 40,
    ) -> torch.Tensor:
        if temperature <= 0:
            raise ValueError("temperature must be greater than zero")
        for _ in range(max_new_tokens):
            context = input_ids[:, -int(self.config["block_size"]) :]
            logits, _ = self(context)
            logits = logits[:, -1, :] / temperature
            if top_k > 0:
                k = min(top_k, logits.size(-1))
                threshold = torch.topk(logits, k).values[:, [-1]]
                logits = logits.masked_fill(logits < threshold, float("-inf"))
            next_token = torch.multinomial(F.softmax(logits, dim=-1), num_samples=1)
            input_ids = torch.cat((input_ids, next_token), dim=1)
            if int(next_token.item()) == 256:
                break
        return input_ids
