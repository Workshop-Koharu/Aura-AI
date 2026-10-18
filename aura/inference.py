from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import torch

from aura.model import AuraTransformer
from aura.tokenizer import ByteTokenizer

DEFAULT_CHECKPOINT = (
    Path(__file__).resolve().parents[1] / "models" / "checkpoints" / "aura-small.pt"
)


class AuraModelNotReady(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model(checkpoint_path: str, modified_ns: int) -> tuple[AuraTransformer, torch.device]:
    del modified_ns
    path = Path(checkpoint_path)
    if not path.is_file():
        raise AuraModelNotReady(
            "Aura의 자체 모델 체크포인트가 없습니다. 먼저 aura.train으로 모델을 학습하세요."
        )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        model = AuraTransformer(checkpoint["config"])
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device).eval()
    except (OSError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise AuraModelNotReady(
            "Aura 모델 파일을 읽을 수 없습니다. 체크포인트를 다시 생성하세요."
        ) from exc
    return model, device


def model_ready() -> bool:
    return Path(os.getenv("AURA_CHECKPOINT_PATH", str(DEFAULT_CHECKPOINT))).is_file()


def generate_reply(messages: list[dict[str, str]], max_new_tokens: int = 180) -> str:
    path = Path(os.getenv("AURA_CHECKPOINT_PATH", str(DEFAULT_CHECKPOINT))).resolve()
    model, device = _load_model(str(path), path.stat().st_mtime_ns if path.exists() else 0)
    tokenizer = ByteTokenizer()
    prompt = (
        "".join(f"{m['role'].capitalize()}: {m['content'].strip()}\n" for m in messages) + "Aura:"
    )
    prompt_ids = tokenizer.encode(prompt, add_bos=True)
    input_ids = torch.tensor(
        [prompt_ids[-int(model.config["block_size"]) :]], dtype=torch.long, device=device
    )
    with torch.inference_mode():
        output = model.generate(input_ids, max_new_tokens=max_new_tokens, temperature=0.8, top_k=40)
    generated = output[0, input_ids.shape[1] :].tolist()
    reply = tokenizer.decode(generated).split("\nUser:", 1)[0].split("\nAssistant:", 1)[0].strip()
    return (
        reply or "아직 자연스러운 답변을 생성하지 못했습니다. 학습 데이터와 학습량을 확인해 주세요."
    )
