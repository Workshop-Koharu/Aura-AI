import torch
from torch import nn
from torch.nn import functional as F
from aura.config import MODEL

class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps

    def forward(self, x):
        scale = torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + self.eps)
        return x * scale.to(x.dtype) * self.weight

class CausalAttention(nn.Module):
    def __init__(self, dim, heads, dropout=0.0):
        super().__init__()
        self.heads, self.head_dim = heads, dim // heads
        self.qkv = nn.Linear(dim, dim * 3, bias=False)
        self.out = nn.Linear(dim, dim, bias=False)
        self.dropout = dropout

    def forward(self, x):
        b, t, c = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        q = q.view(b, t, self.heads, self.head_dim).transpose(1, 2)
        k = k.view(b, t, self.heads, self.head_dim).transpose(1, 2)
        v = v.view(b, t, self.heads, self.head_dim).transpose(1, 2)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True, dropout_p=self.dropout if self.training else 0.0)
        return self.out(y.transpose(1, 2).contiguous().view(b, t, c))

class Block(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.norm1 = RMSNorm(cfg.d_model)
        self.attn = CausalAttention(cfg.d_model, cfg.n_heads, cfg.dropout)
        self.norm2 = RMSNorm(cfg.d_model)
        self.mlp = nn.Sequential(nn.Linear(cfg.d_model, cfg.d_ff), nn.GELU(), nn.Linear(cfg.d_ff, cfg.d_model))

    def forward(self, x):
        x = x + self.attn(self.norm1(x))
        return x + self.mlp(self.norm2(x))

class PatchEncoder(nn.Module):
    def __init__(self, width, layers, patch, image_size):
        super().__init__()
        self.patch = nn.Conv2d(3, width, kernel_size=patch, stride=patch)
        self.pos = nn.Parameter(torch.zeros(1, (image_size // patch) ** 2, width))
        layer = nn.TransformerEncoderLayer(width, 8, width * 4, batch_first=True, norm_first=True, activation="gelu")
        self.encoder = nn.TransformerEncoder(layer, layers)
        self.norm = nn.LayerNorm(width)

    def forward(self, image):
        x = self.patch(image).flatten(2).transpose(1, 2)
        return self.norm(self.encoder(x + self.pos).mean(1))

class AudioEncoder(nn.Module):
    def __init__(self, width, layers):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, stride=2, padding=1), nn.GELU(),
            nn.Conv2d(32, 96, 3, stride=2, padding=1), nn.GELU(),
            nn.Conv2d(96, width, 3, stride=2, padding=1), nn.GELU(),
        )
        layer = nn.TransformerEncoderLayer(width, 8, width * 4, batch_first=True, norm_first=True, activation="gelu")
        self.encoder = nn.TransformerEncoder(layer, layers)
        self.norm = nn.LayerNorm(width)

    def forward(self, spec):
        x = self.conv(spec).mean(2).transpose(1, 2)
        return self.norm(self.encoder(x).mean(1))

class AuraModel(nn.Module):
    def __init__(self, cfg=MODEL):
        super().__init__()
        self.cfg = cfg
        self.token = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.position = nn.Embedding(cfg.max_seq_len + 2, cfg.d_model)
        self.blocks = nn.ModuleList([Block(cfg) for _ in range(cfg.n_layers)])
        self.norm = RMSNorm(cfg.d_model)
        self.lm_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        self.lm_head.weight = self.token.weight
        self.image_encoder = PatchEncoder(cfg.image_width, cfg.image_layers, cfg.image_patch, cfg.image_size)
        self.image_project = nn.Linear(cfg.image_width, cfg.d_model)
        self.audio_encoder = AudioEncoder(cfg.audio_width, cfg.audio_layers)
        self.audio_project = nn.Linear(cfg.audio_width, cfg.d_model)
        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None: nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, input_ids, image=None, audio=None, labels=None):
        x = self.token(input_ids)
        prefixes = []
        if image is not None: prefixes.append(self.image_project(self.image_encoder(image)).unsqueeze(1))
        if audio is not None: prefixes.append(self.audio_project(self.audio_encoder(audio)).unsqueeze(1))
        if prefixes: x = torch.cat(prefixes + [x], dim=1)
        positions = torch.arange(x.shape[1], device=x.device)
        x = x + self.position(positions).unsqueeze(0)
        for block in self.blocks: x = block(x)
        logits = self.lm_head(self.norm(x))
        loss = None
        if labels is not None:
            prefix_count = logits.shape[1] - labels.shape[1]
            target = torch.cat([torch.full((labels.shape[0], prefix_count), -100, device=labels.device, dtype=labels.dtype), labels], dim=1)
            loss = F.cross_entropy(logits[:, :-1].reshape(-1, logits.shape[-1]), target[:, 1:].reshape(-1), ignore_index=-100)
        return logits, loss

    @torch.inference_mode()
    def generate(self, input_ids, max_new_tokens=128, temperature=0.8, top_k=40, image=None, audio=None):
        self.eval()
        for _ in range(max_new_tokens):
            context = input_ids[:, -self.cfg.max_seq_len:]
            logits, _ = self(context, image=image, audio=audio)
            next_logits = logits[:, -1, :] / max(temperature, 1e-4)
            if top_k:
                values, _ = torch.topk(next_logits, min(top_k, next_logits.size(-1)))
                next_logits[next_logits < values[:, [-1]]] = -float("inf")
            next_id = torch.multinomial(torch.softmax(next_logits, dim=-1), num_samples=1)
            input_ids = torch.cat([input_ids, next_id], dim=1)
            if next_id.item() == 258: break
        return input_ids
