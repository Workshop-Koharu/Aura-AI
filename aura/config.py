from dataclasses import dataclass
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHECKPOINTS = DATA / "checkpoints"
TOKENIZER_PATH = DATA / "tokenizer" / "aura-bpe.json"

@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int = 2308
    d_model: int = 512
    n_layers: int = 12
    n_heads: int = 8
    d_ff: int = 2048
    max_seq_len: int = 512
    image_size: int = 224
    image_patch: int = 16
    image_width: int = 256
    image_layers: int = 6
    audio_width: int = 256
    audio_layers: int = 4
    dropout: float = 0.0

MODEL = ModelConfig()
TRAINING = {
    "device": "cpu",
    "torch_threads": 4,
    "cpu_affinity_logical_cpus": 4,
    "ram_budget_gb": 5.0,
    "batch_size": 1,
    "gradient_accumulation": 1,
    "sequence_length": 256,
    "learning_rate": 2e-4,
    "weight_decay": 0.1,
    "warmup_steps": 500,
    "checkpoint_every": 250,
    "sleep_seconds_per_step": 0.75,
    "max_steps_per_session": 1000000,
    "mixed_precision": False,
}
