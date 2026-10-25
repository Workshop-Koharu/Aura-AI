from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path, PurePosixPath

ATTRIBUTION = "\ubcf8 AI\ub370\uc774\ud130 \ub4f1\uc744 \uc774\uc6a9\ud560 \ub54c\uc5d0\ub294 \ubc18\ub4dc\uc2dc \ud55c\uad6d\uc9c0\ub2a5\uc815\ubcf4\uc0ac\ud68c\uc9c4\ud765\uc6d0\uc758 \uc0ac\uc5c5\uacb0\uacfc\uc784\uc744 \ubc1d\ud600\uc57c \ud558\uba70, \ubcf8 AI\ub370\uc774\ud130\ub97c \uc774\uc6a9\ud55c 2\ucc28\uc801 \uc800\uc791\ubb3c\uc5d0\ub3c4 \ub3d9\uc77c\ud558\uac8c \ubc1d\ud600\uc57c \ud569\ub2c8\ub2e4."
PROMPT_KEYS = ("instruction", "question", "prompt", "query", "request", "user", "input")
ANSWER_KEYS = ("output", "response", "answer", "assistant", "completion", "target", "result")
ROLE_KEYS = ("role", "from", "speaker", "author")
CONTENT_KEYS = ("content", "value", "text", "message")


def decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def scalar(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def pick(mapping: dict, keys: tuple[str, ...]) -> str:
    lowered = {str(key).lower(): value for key, value in mapping.items()}
    for key in keys:
        value = scalar(lowered.get(key))
        if value:
            return value
    return ""


def pair(prompt: str, answer: str) -> str | None:
    prompt, answer = prompt.strip(), answer.strip()
    if len(prompt) < 1 or len(answer) < 1 or len(prompt) > 100_000 or len(answer) > 100_000:
        return None
    return f"User: {prompt}\nAura: {answer}\n"


def extract_pairs(value: object):
    if isinstance(value, dict):
        lowered = {str(key).lower(): child for key, child in value.items()}
        prompt = pick(value, PROMPT_KEYS)
        answer = pick(value, ANSWER_KEYS)
        instruction = scalar(lowered.get("instruction"))
        input_text = scalar(lowered.get("input"))
        if instruction and input_text and prompt == instruction:
            prompt = f"{instruction}\n{input_text}"
        extra = pick(value, ("context", "background"))
        if prompt and answer:
            if extra and not input_text:
                prompt = f"{prompt}\nContext: {extra}"
            formatted = pair(prompt, answer)
            if formatted:
                yield formatted
                return
        for key, child in value.items():
            if str(key).lower() in (
                "messages",
                "conversations",
                "conversation",
                "dialog",
                "dialogue",
            ) and isinstance(child, list):
                pending_user = ""
                for message in child:
                    if not isinstance(message, dict):
                        continue
                    role = pick(message, ROLE_KEYS).lower()
                    content = pick(message, CONTENT_KEYS)
                    if role in ("user", "human", "prompter", "question"):
                        pending_user = content
                    elif role in ("assistant", "gpt", "bot", "system") and pending_user and content:
                        formatted = pair(pending_user, content)
                        if formatted:
                            yield formatted
                        pending_user = ""
            else:
                yield from extract_pairs(child)
    elif isinstance(value, list):
        for child in value:
            yield from extract_pairs(child)


def parse_data(raw: bytes, name: str, depth: int = 0):
    ext = PurePosixPath(name.replace("\\", "/")).suffix.lower()
    if ext == ".zip":
        if depth >= 8:
            return
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    try:
                        yield from parse_data(
                            archive.read(info), f"{name}!/{info.filename}", depth + 1
                        )
                    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
                        print(f"WARN zip member {name}!/{info.filename}: {exc}")
        except (zipfile.BadZipFile, OSError):
            return
        return
    if ext in (".json", ".jsonl", ".ndjson"):
        text = decode(raw)
        if ext == ".json":
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                return
            yield from extract_pairs(obj)
        else:
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    yield from extract_pairs(json.loads(line))
                except json.JSONDecodeError:
                    continue
    elif ext in (".csv", ".tsv"):
        try:
            reader = csv.DictReader(
                io.StringIO(decode(raw)), delimiter="\t" if ext == ".tsv" else ","
            )
            for row in reader:
                prompt = pick(row, PROMPT_KEYS)
                answer = pick(row, ANSWER_KEYS)
                formatted = pair(prompt, answer)
                if formatted:
                    yield formatted
        except (csv.Error, UnicodeError):
            return


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract instruction/response pairs from Aura's permitted instruction-tuning source archives."
    )
    parser.add_argument("--source", type=Path, default=Path("data/source"))
    parser.add_argument("--output", type=Path, default=Path("data/dialogue_train.txt"))
    parser.add_argument("--manifest", type=Path, default=Path("data/DIALOGUE_SOURCES.csv"))
    args = parser.parse_args()
    root = args.source.resolve()
    target_dirs = [p for p in root.iterdir() if p.is_dir() and "Instruction Tuning" in p.name]
    if not target_dirs:
        parser.error(f"No Instruction Tuning dataset folders found under {root}")
    files = sorted(file for folder in target_dirs for file in folder.rglob("*") if file.is_file())
    seen: set[str] = set()
    manifest: list[tuple[str, int, str]] = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as out:
        out.write("AURA CHAT INSTRUCTION CORPUS\nDataset attribution: " + ATTRIBUTION + "\n\n")
        for index, path in enumerate(files, 1):
            try:
                raw = path.read_bytes()
            except OSError as exc:
                print(f"WARN unreadable {path}: {exc}")
                continue
            for example in parse_data(raw, path.relative_to(root).as_posix()):
                digest = hashlib.sha256(example.encode("utf-8")).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                out.write("\n" + example + "\n")
                manifest.append(
                    (path.relative_to(root).as_posix(), len(example.encode("utf-8")), digest)
                )
            if index % 20 == 0:
                print(
                    f"scanned {index}/{len(files)} files; unique examples {len(seen):,}", flush=True
                )
    with args.manifest.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_path", "example_utf8_bytes", "sha256"])
        writer.writerows(manifest)
    print(f"Complete: {len(files):,} files scanned; {len(seen):,} unique dialogue examples")
    print(f"Dialogue corpus: {args.output.resolve()} ({args.output.stat().st_size:,} bytes)")
    print(f"Source manifest: {args.manifest.resolve()}")


if __name__ == "__main__":
    main()
