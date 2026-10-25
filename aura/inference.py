from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

import torch

from aura.model import AuraTransformer
from aura.tokenizer import ByteTokenizer

DEFAULT_CHECKPOINT = (
    Path(__file__).resolve().parents[1] / "models" / "checkpoints" / "aura-small.pt"
)
MAX_CONTEXT_BYTES = 256
MAX_GENERATION_TOKENS = 64


class AuraModelNotReady(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model(checkpoint_path: str, modified_ns: int) -> tuple[AuraTransformer, torch.device]:
    del modified_ns
    path = Path(checkpoint_path)
    if not path.is_file():
        raise AuraModelNotReady(
            "Aura 자체 모델 체크포인트가 없습니다. 먼저 aura.train으로 모델을 학습하세요."
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
    path = Path(os.getenv("AURA_CHECKPOINT_PATH", str(DEFAULT_CHECKPOINT)))
    if not path.is_file():
        return False
    try:
        _load_model(str(path.resolve()), path.stat().st_mtime_ns)
        return True
    except AuraModelNotReady:
        return False


def _looks_like_usable_text(reply: str, messages: list[dict[str, str]]) -> bool:
    """Reject obvious token/debug noise; never claim a rejected completion is an answer."""
    text = reply.strip()
    if (
        len(text) < 6
        or "\ufffd" in text
        or "_" in text
        or sum(not ch.isalnum() and not ch.isspace() for ch in text) / max(len(text), 1) > 0.35
        or re.search(r"data\s*\[\s*\d+\s*\]|(?:\\x[0-9a-f]{2}){2,}", text, re.IGNORECASE)
        or re.search(r"(\w)\1{5,}", text)
    ):
        return False
    latest = messages[-1]["content"] if messages else ""
    korean_request = bool(re.search(r"[가-힣]", latest))
    if korean_request:
        hangul = len(re.findall(r"[가-힣]", text))
        letters = len(re.findall(r"[A-Za-z가-힣]", text))
        if hangul < 3 or (letters and hangul / letters < 0.3):
            return False
    return True


def generate_reply(
    messages: list[dict[str, str]], max_new_tokens: int = MAX_GENERATION_TOKENS
) -> str:
    """Generate a deliberately short reply to reduce CPU latency and proxy timeouts."""
    if not 1 <= max_new_tokens <= MAX_GENERATION_TOKENS:
        raise ValueError(f"max_new_tokens must be between 1 and {MAX_GENERATION_TOKENS}")
    path = Path(os.getenv("AURA_CHECKPOINT_PATH", str(DEFAULT_CHECKPOINT))).resolve()
    try:
        model, device = _load_model(str(path), path.stat().st_mtime_ns if path.exists() else 0)
    except OSError as exc:
        raise AuraModelNotReady("Aura 모델 체크포인트 파일을 열 수 없습니다.") from exc
    tokenizer = ByteTokenizer()
    prompt = (
        "".join(f"{m['role'].capitalize()}: {m['content'].strip()}\n" for m in messages) + "Aura:"
    )
    prompt_ids = tokenizer.encode(prompt)
    context_limit = min(MAX_CONTEXT_BYTES, int(model.config["block_size"]))
    input_ids = torch.tensor([prompt_ids[-context_limit:]], dtype=torch.long, device=device)
    with torch.inference_mode():
        output = model.generate(input_ids, max_new_tokens=max_new_tokens, temperature=0.8, top_k=40)
    generated = output[0, input_ids.shape[1] :].tolist()
    reply = tokenizer.decode(generated).split("\nUser:", 1)[0].split("\nAssistant:", 1)[0].strip()
    if not _looks_like_usable_text(reply, messages):
        return "아직 자연스러운 답변을 생성하지 못했습니다. Aura는 현재 소형 실험 모델이며, 더 많은 학습과 대화 형식의 데이터 학습이 필요합니다."
    return reply
