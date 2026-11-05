from pathlib import Path
import json
from mcp.server.fastmcp import FastMCP
from aura.config import DATA, MODEL, TRAINING
from aura.engine import ENGINE
from aura.training.runner import RUNNER

mcp = FastMCP("Aura AI Local")

@mcp.tool()
def health() -> dict:
    """Return local Aura API and training availability."""
    return {"ok": True, "engine": "from-scratch", "training": RUNNER.status()}

@mcp.tool()
def model_info() -> dict:
    """Return model architecture, parameter budget and resource limits."""
    return {"architecture": MODEL.__dict__, "resource_limits": TRAINING, **ENGINE.status()}

@mcp.tool()
def generate_text(prompt: str, max_tokens: int = 160) -> dict:
    """Generate text using Aura's locally trained, randomly initialized model."""
    text, meta = ENGINE.generate(prompt, max_new_tokens=max_tokens)
    return {"text": text, "meta": meta}

@mcp.tool()
def generate_with_image(prompt: str, image_path: str, max_tokens: int = 160) -> dict:
    """Condition local generation on an image file stored inside Aura data/."""
    path = (DATA / image_path).resolve()
    if DATA.resolve() not in path.parents or not path.is_file(): raise ValueError("Image path must be inside Aura data/.")
    text, meta = ENGINE.generate(prompt, image_bytes=path.read_bytes(), max_new_tokens=max_tokens)
    return {"text": text, "meta": meta}

@mcp.tool()
def generate_with_audio(prompt: str, audio_path: str, max_tokens: int = 160) -> dict:
    """Condition local generation on a 16-bit PCM WAV file inside Aura data/."""
    path = (DATA / audio_path).resolve()
    if DATA.resolve() not in path.parents or not path.is_file(): raise ValueError("Audio path must be inside Aura data/.")
    text, meta = ENGINE.generate(prompt, audio_bytes=path.read_bytes(), max_new_tokens=max_tokens)
    return {"text": text, "meta": meta}

@mcp.tool()
def training_status() -> dict:
    """Read training step, loss and worker status."""
    return RUNNER.status()

@mcp.tool()
def start_training() -> dict:
    """Start slow local training from random initialization using the user's dataset."""
    return RUNNER.start()

@mcp.tool()
def stop_training() -> dict:
    """Request a graceful stop; the latest checkpoint is saved."""
    return RUNNER.stop()

@mcp.tool()
def list_datasets() -> dict:
    """List text, image-caption and audio-transcript training files."""
    return {name: [str(p.relative_to(DATA)).replace("\\", "/") for p in (DATA / name).rglob("*") if p.is_file()] for name in ("text", "image_text", "audio_text")}

@mcp.tool()
def add_text_data(filename: str, text: str) -> dict:
    """Add UTF-8 training text to data/text. This does not start training."""
    safe = Path(filename).name
    if not safe.endswith(".txt"): safe += ".txt"
    folder = DATA / "text"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / safe
    target.write_text(text, encoding="utf-8")
    return {"saved": str(target.relative_to(DATA)), "characters": len(text)}

@mcp.tool()
def register_image_caption(image_path: str, caption: str) -> dict:
    """Register an image and its caption for from-scratch image-text training."""
    path = (DATA / image_path).resolve()
    if DATA.resolve() not in path.parents or not path.is_file(): raise ValueError("Image path must be inside Aura data/.")
    index = DATA / "image_text" / "pairs.jsonl"
    index.parent.mkdir(parents=True, exist_ok=True)
    with index.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"file": path.relative_to(DATA).as_posix(), "text": caption}, ensure_ascii=False) + "\n")
    return {"registered": path.relative_to(DATA).as_posix()}

@mcp.tool()
def register_audio_transcript(audio_path: str, transcript: str) -> dict:
    """Register a 16-bit PCM WAV and transcript for from-scratch audio-text training."""
    from aura.multimodal.preprocess import wav_spectrogram
    path = (DATA / audio_path).resolve()
    if DATA.resolve() not in path.parents or not path.is_file(): raise ValueError("Audio path must be inside Aura data/.")
    wav_spectrogram(path.read_bytes())
    index = DATA / "audio_text" / "pairs.jsonl"
    index.parent.mkdir(parents=True, exist_ok=True)
    with index.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"file": path.relative_to(DATA).as_posix(), "text": transcript}, ensure_ascii=False) + "\n")
    return {"registered": path.relative_to(DATA).as_posix()}

if __name__ == "__main__":
    mcp.run(transport="stdio")
