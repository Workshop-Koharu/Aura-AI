from __future__ import annotations

import argparse
import random
from pathlib import Path

import torch

from aura.model import AuraTransformer
from aura.tokenizer import ByteTokenizer

DEFAULT_CONFIG: dict[str, int | float] = {
    "vocab_size": ByteTokenizer.VOCAB_SIZE,
    "block_size": 128,
    "n_embd": 128,
    "n_head": 4,
    "n_layer": 4,
    "dropout": 0.1,
}


def get_batch(
    data: torch.Tensor, batch_size: int, block_size: int, device: torch.device
) -> tuple[torch.Tensor, torch.Tensor]:
    starts = torch.randint(0, len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[int(i) : int(i) + block_size] for i in starts])
    y = torch.stack([data[int(i) + 1 : int(i) + block_size + 1] for i in starts])
    return x.to(device), y.to(device)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train Aura from random initialization on your own text corpus."
    )
    parser.add_argument("--data", type=Path, default=Path("data/train.txt"))
    parser.add_argument("--output", type=Path, default=Path("models/checkpoints/aura-small.pt"))
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1 or args.learning_rate <= 0:
        parser.error("steps, batch-size and learning-rate must be positive")
    if not args.data.is_file():
        parser.error(
            f"Corpus not found: {args.data}. Create it using text you have permission to use."
        )
    tokenizer = ByteTokenizer()
    token_ids = tokenizer.encode(args.data.read_text(encoding="utf-8"), add_bos=True, add_eos=True)
    block_size = int(DEFAULT_CONFIG["block_size"])
    if len(token_ids) < block_size + 20:
        parser.error(
            f"Corpus too small: need at least {block_size + 20} tokens; found {len(token_ids)}."
        )
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA requested but no CUDA GPU is available to PyTorch.")
    device = torch.device(
        "cuda"
        if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available())
        else "cpu"
    )
    split = min(max(block_size + 2, int(len(token_ids) * 0.95)), len(token_ids) - block_size - 1)
    all_data = torch.tensor(token_ids, dtype=torch.long)
    train_data, val_data = all_data[:split], all_data[split:]
    if len(val_data) < block_size + 2:
        val_data = train_data[-(block_size + 2) :]
    model = AuraTransformer(DEFAULT_CONFIG).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    print(
        f"Device: {device}; tokens: {len(token_ids):,}; parameters: {sum(p.numel() for p in model.parameters()):,}"
    )
    model.train()
    for step in range(1, args.steps + 1):
        xb, yb = get_batch(train_data, args.batch_size, block_size, device)
        _, loss = model(xb, yb)
        assert loss is not None
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if step == 1 or step % 100 == 0 or step == args.steps:
            model.eval()
            with torch.no_grad():
                vx, vy = get_batch(val_data, min(args.batch_size, 8), block_size, device)
                _, val_loss = model(vx, vy)
            print(
                f"step {step:5d}/{args.steps} | train loss {loss.item():.4f} | val loss {val_loss.item():.4f}"
            )
            model.train()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "format_version": 1,
            "config": DEFAULT_CONFIG,
            "model_state_dict": model.cpu().state_dict(),
            "training": {
                "steps": args.steps,
                "seed": args.seed,
                "tokens": len(token_ids),
                "corpus": str(args.data),
            },
        },
        args.output,
    )
    print(f"Saved checkpoint: {args.output.resolve()}")
    print(
        "This is a small experimental model; successful training does not imply broad knowledge or reliable answers."
    )


if __name__ == "__main__":
    main()
