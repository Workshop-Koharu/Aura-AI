from __future__ import annotations

import argparse
import mmap
import random
from pathlib import Path

import torch

from aura.model import AuraTransformer
from aura.tokenizer import ByteTokenizer

DEFAULT_CONFIG: dict[str, int | float] = {
    "vocab_size": ByteTokenizer.VOCAB_SIZE,
    "block_size": 256,
    "n_embd": 256,
    "n_head": 4,
    "n_layer": 6,
    "dropout": 0.1,
}


def get_batch(
    corpus: mmap.mmap,
    start_min: int,
    start_max: int,
    batch_size: int,
    block_size: int,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Sample only one small batch from a memory-mapped UTF-8 corpus.

    The corpus stays on disk; only batch_size * (block_size + 1) bytes are copied
    into RAM. Byte token IDs are the UTF-8 byte values, so decoding boundaries
    do not affect next-byte training.
    """
    if start_max <= start_min:
        raise ValueError("Training/validation split is too small for the selected block size")
    starts = [random.randrange(start_min, start_max) for _ in range(batch_size)]
    xs, ys = [], []
    for start in starts:
        raw = bytearray(corpus[start : start + block_size + 1])
        row = torch.frombuffer(raw, dtype=torch.uint8).to(dtype=torch.long)
        xs.append(row[:-1])
        ys.append(row[1:])
    return torch.stack(xs).to(device), torch.stack(ys).to(device)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train Aura from random initialization using memory-mapped byte batches."
    )
    parser.add_argument("--data", type=Path, default=Path("data/train.txt"))
    parser.add_argument(
        "--dialogue-data",
        type=Path,
        default=None,
        help="Optional normalized instruction/response corpus mixed into every batch",
    )
    parser.add_argument("--output", type=Path, default=Path("models/checkpoints/aura-small.pt"))
    parser.add_argument(
        "--init-checkpoint",
        type=Path,
        default=None,
        help="Initialize model weights from a compatible Aura checkpoint; optimizer starts fresh",
    )
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--checkpoint-every", type=int, default=500)
    parser.add_argument(
        "--threads", type=int, default=2, help="CPU thread cap; use 1-4 on memory-constrained PCs"
    )
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1 or args.learning_rate <= 0:
        parser.error("steps, batch-size and learning-rate must be positive")
    if args.log_every < 1 or args.checkpoint_every < 0 or args.threads < 1:
        parser.error("log-every/threads must be positive and checkpoint-every cannot be negative")
    if not args.data.is_file():
        parser.error(f"Corpus not found: {args.data}")
    block_size = int(DEFAULT_CONFIG["block_size"])
    corpus_bytes = args.data.stat().st_size
    if corpus_bytes < block_size * 2 + 20:
        parser.error(
            f"Corpus too small: need at least {block_size * 2 + 20} bytes; found {corpus_bytes}."
        )
    dialogue_bytes = 0
    if args.dialogue_data is not None:
        if not args.dialogue_data.is_file():
            parser.error(f"Dialogue corpus not found: {args.dialogue_data}")
        dialogue_bytes = args.dialogue_data.stat().st_size
        if dialogue_bytes < block_size * 2 + 20:
            parser.error("Dialogue corpus is too small for the selected block size.")
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA requested but no CUDA GPU is available to PyTorch.")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    device = torch.device(
        "cuda"
        if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available())
        else "cpu"
    )
    split = int(corpus_bytes * 0.95)
    split = min(max(split, block_size + 1), corpus_bytes - block_size - 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    model = AuraTransformer(DEFAULT_CONFIG)
    if args.init_checkpoint is not None:
        if not args.init_checkpoint.is_file():
            parser.error(f"Initial checkpoint not found: {args.init_checkpoint}")
        checkpoint = torch.load(args.init_checkpoint, map_location="cpu", weights_only=True)
        if checkpoint.get("config") != DEFAULT_CONFIG:
            parser.error("Initial checkpoint configuration does not match DEFAULT_CONFIG.")
        model.load_state_dict(checkpoint["model_state_dict"])
        print(f"Initialized weights from {args.init_checkpoint.resolve()}", flush=True)
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    parameters = sum(p.numel() for p in model.parameters())
    print(
        f"Device: {device}; corpus bytes: {corpus_bytes:,}; parameters: {parameters:,}; batch: {args.batch_size}; CPU threads: {args.threads}",
        flush=True,
    )
    print(
        "RAM optimization: corpus is memory-mapped; only sampled batches are copied to RAM.",
        flush=True,
    )

    def save(step: int) -> None:
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        torch.save(
            {
                "format_version": 2,
                "config": DEFAULT_CONFIG,
                "model_state_dict": model.cpu().state_dict(),
                "training": {
                    "steps": step,
                    "target_steps": args.steps,
                    "seed": args.seed,
                    "corpus_bytes": corpus_bytes,
                    "corpus": str(args.data),
                    "batch_size": args.batch_size,
                    "device": str(device),
                    "dialogue_data": str(args.dialogue_data) if args.dialogue_data else None,
                    "init_checkpoint": str(args.init_checkpoint) if args.init_checkpoint else None,
                },
            },
            temporary,
        )
        temporary.replace(args.output)
        model.to(device)
        print(f"Checkpoint saved at step {step}: {args.output.resolve()}", flush=True)

    dialogue_handle = args.dialogue_data.open("rb") if args.dialogue_data else None
    dialogue_mapped = (
        mmap.mmap(dialogue_handle.fileno(), length=0, access=mmap.ACCESS_READ)
        if dialogue_handle
        else None
    )
    dialogue_split = int(dialogue_bytes * 0.95) if dialogue_mapped else 0
    with args.data.open("rb") as handle:  # noqa: SIM117
        with mmap.mmap(handle.fileno(), length=0, access=mmap.ACCESS_READ) as mapped:
            model.train()
            for step in range(1, args.steps + 1):
                if dialogue_mapped is not None:
                    dialogue_batch = max(1, args.batch_size // 2)
                    corpus_batch = args.batch_size - dialogue_batch
                    batches = []
                    if corpus_batch:
                        batches.append(
                            get_batch(
                                mapped, 0, split - block_size - 1, corpus_batch, block_size, device
                            )
                        )
                    batches.append(
                        get_batch(
                            dialogue_mapped,
                            0,
                            dialogue_split - block_size - 1,
                            dialogue_batch,
                            block_size,
                            device,
                        )
                    )
                    xb = torch.cat([batch[0] for batch in batches], dim=0)
                    yb = torch.cat([batch[1] for batch in batches], dim=0)
                else:
                    xb, yb = get_batch(
                        mapped, 0, split - block_size - 1, args.batch_size, block_size, device
                    )
                optimizer.zero_grad(set_to_none=True)
                _, loss = model(xb, yb)
                assert loss is not None
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                if step == 1 or step % args.log_every == 0 or step == args.steps:
                    model.eval()
                    with torch.inference_mode():
                        vx, vy = get_batch(
                            mapped,
                            split,
                            corpus_bytes - block_size - 1,
                            min(args.batch_size, 2),
                            block_size,
                            device,
                        )
                        _, val_loss = model(vx, vy)
                    print(
                        f"step {step:6d}/{args.steps} | train loss {loss.item():.4f} | val loss {val_loss.item():.4f}",
                        flush=True,
                    )
                    model.train()
                if args.checkpoint_every and step % args.checkpoint_every == 0:
                    save(step)
            save(args.steps)
    if dialogue_mapped is not None:
        dialogue_mapped.close()
        dialogue_handle.close()
    print(
        "Training complete. Loss reduction alone does not guarantee answer quality or factuality.",
        flush=True,
    )


if __name__ == "__main__":
    main()
