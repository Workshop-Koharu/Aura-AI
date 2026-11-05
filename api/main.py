import base64
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image
from aura.config import ROOT, DATA, MODEL, TRAINING
from aura.engine import ENGINE
from aura.training.runner import RUNNER
from aura.multimodal.preprocess import wav_spectrogram

app = FastAPI(title="Aura AI API", version="0.1.0")

@app.middleware("http")
async def require_gateway_secret(request, call_next):
    secret = os.getenv("AURA_GATEWAY_SECRET", "")
    if secret and request.url.path != "/api/health":
        if request.headers.get("x-aura-gateway-key") != secret:
            return JSONResponse(status_code=401, content={"error": "Unauthorized inference gateway."})
    return await call_next(request)


app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")
app.mount("/web", StaticFiles(directory=ROOT / "web"), name="web")

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    image_base64: str | None = None
    audio_base64: str | None = None
    files: list[dict] = Field(default_factory=list)
    max_tokens: int = Field(default=160, ge=1, le=512)

class OpenAIMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: str = "aura-from-scratch"
    messages: list[OpenAIMessage]
    max_tokens: int = Field(default=160, ge=1, le=512)
    stream: bool = False

class TextData(BaseModel):
    filename: str = Field(default="notes.txt", max_length=100)
    text: str = Field(min_length=1, max_length=2_000_000)

def decode_file(value):
    if not value: return None
    try:
        if "," in value: value = value.split(",", 1)[1]
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise HTTPException(400, "Invalid base64 attachment.") from exc


def extract_document_text(filename: str, content_type: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".css", ".xml", ".yaml", ".yml", ".log"} or content_type.startswith("text/"):
        return raw.decode("utf-8-sig", errors="replace")[:120000]
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(__import__("io").BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages[:80])[:120000]
    if suffix == ".docx":
        from docx import Document
        doc = Document(__import__("io").BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)[:120000]
    if suffix == ".xlsx":
        from openpyxl import load_workbook
        book = load_workbook(__import__("io").BytesIO(raw), read_only=True, data_only=True)
        rows = []
        for sheet in book.worksheets[:10]:
            rows.append(f"[시트: {sheet.title}]")
            for row in sheet.iter_rows(max_row=500, values_only=True):
                rows.append(" | ".join("" if v is None else str(v) for v in row))
        return "\n".join(rows)[:120000]
    if suffix == ".pptx":
        from pptx import Presentation
        deck = Presentation(__import__("io").BytesIO(raw))
        lines = []
        for slide in deck.slides[:80]:
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    lines.append(shape.text)
        return "\n".join(lines)[:120000]
    return ""

def append_pair(kind, relative, text):
    folder = DATA / ("image_text" if kind == "image" else "audio_text")
    folder.mkdir(parents=True, exist_ok=True)
    index = folder / "pairs.jsonl"
    with index.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"file": relative, "text": text}, ensure_ascii=False) + "\n")

@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")

@app.get("/api/health")
def health():
    return {"ok": True, "engine": "aura-from-scratch", "device": ENGINE.status()["device"], "training": RUNNER.status()["status"]}

@app.get("/api/model/status")
def model_status():
    return {**ENGINE.status(), "training": RUNNER.status(), "architecture": MODEL.__dict__, "resource_limits": TRAINING}

@app.get("/api/training/status")
def training_status():
    return RUNNER.status()

@app.post("/api/training/start")
def start_training():
    result = RUNNER.start()
    if not result.get("started") and result.get("reason") != "already_running":
        raise HTTPException(409, result.get("reason", "Could not start training."))
    return result

@app.post("/api/training/stop")
def stop_training():
    return RUNNER.stop()

@app.get("/api/datasets")
def datasets():
    result = {}
    for name in ("text", "image_text", "audio_text"):
        folder = DATA / name
        result[name] = [str(p.relative_to(DATA)).replace("\\", "/") for p in folder.rglob("*") if p.is_file()]
    return result

@app.post("/api/datasets/text")
def add_text(body: TextData):
    folder = DATA / "text"
    folder.mkdir(parents=True, exist_ok=True)
    safe = Path(body.filename).name
    if not safe.lower().endswith(".txt"): safe += ".txt"
    target = folder / safe
    target.write_text(body.text, encoding="utf-8")
    return {"saved": str(target.relative_to(DATA)), "characters": len(body.text)}

@app.post("/api/datasets/image")
async def add_image(caption: str = Form(...), file: UploadFile = File(...)):
    if not caption.strip():
        raise HTTPException(422, "An image caption is required for training.")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(415, "Image file required.")
    raw = await file.read()
    if len(raw) > 15 * 1024 * 1024: raise HTTPException(413, "Image exceeds 15 MB.")
    try: Image.open(raw if hasattr(raw, "read") else __import__("io").BytesIO(raw)).verify()
    except Exception as exc: raise HTTPException(400, "Invalid image file.") from exc
    folder = DATA / "image_text" / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    name = Path(file.filename or "image.png").name
    ext = Path(name).suffix.lower() or ".png"
    target = folder / (str(__import__("uuid").uuid4()) + ext)
    target.write_bytes(raw)
    relative = target.relative_to(DATA).as_posix()
    append_pair("image", relative, caption)
    return {"saved": relative}

@app.post("/api/datasets/audio")
async def add_audio(transcript: str = Form(...), file: UploadFile = File(...)):
    if not transcript.strip():
        raise HTTPException(422, "An audio transcript is required for training.")
    raw = await file.read()
    if len(raw) > 25 * 1024 * 1024: raise HTTPException(413, "Audio exceeds 25 MB.")
    try: wav_spectrogram(raw)
    except Exception as exc: raise HTTPException(400, "A valid 16-bit PCM WAV file is required.") from exc
    folder = DATA / "audio_text" / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (str(__import__("uuid").uuid4()) + ".wav")
    target.write_bytes(raw)
    relative = target.relative_to(DATA).as_posix()
    append_pair("audio", relative, transcript)
    return {"saved": relative}

@app.post("/api/chat")
def chat(body: ChatRequest):
    image = decode_file(body.image_base64)
    audio = decode_file(body.audio_base64)
    prompt = body.message
    for item in body.files[:5]:
        name = Path(str(item.get("name", "attachment"))).name
        raw = decode_file(item.get("base64"))
        if not raw:
            continue
        if len(raw) > 3 * 1024 * 1024:
            raise HTTPException(413, f"{name}: 파일은 3MB 이하만 처리할 수 있습니다.")
        mime = str(item.get("type", ""))
        suffix = Path(name).suffix.lower()
        if mime.startswith("image/") and image is None:
            image = raw
        elif mime.startswith("audio/") and audio is None:
            audio = raw
        else:
            try:
                extracted = extract_document_text(name, mime, raw)
            except ImportError as exc:
                raise HTTPException(503, "문서 분석 패키지가 설치되지 않았습니다. Colab 환경을 다시 설치하세요.") from exc
            except Exception as exc:
                raise HTTPException(400, f"{name}: 문서 내용을 읽지 못했습니다: {exc}") from exc
            if extracted.strip():
                prompt += f"\n\n[첨부 문서: {name}]\n{extracted}"
            elif suffix not in {".png", ".jpg", ".jpeg", ".webp", ".wav"}:
                prompt += f"\n\n[첨부 파일: {name}] 텍스트를 추출할 수 없는 형식입니다."
    try:
        text, meta = ENGINE.generate(prompt[:20000], image, audio, body.max_tokens)
        return {"text": text, "meta": meta}
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

@app.post("/api/chat/stream")
def chat_stream(body: ChatRequest):
    result = chat(body)
    def events():
        yield "data: " + json.dumps({"delta": result["text"], "done": True}, ensure_ascii=False) + "\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(events(), media_type="text/event-stream")

@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": "aura-from-scratch", "object": "model", "owned_by": "local"}]}

@app.post("/v1/chat/completions")
def openai_compatible(body: OpenAIChatRequest):
    prompt = "\n".join(m.content for m in body.messages if m.role in ("system", "user", "assistant"))
    try:
        text, meta = ENGINE.generate(prompt, max_new_tokens=body.max_tokens)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"id": "aura-local", "object": "chat.completion", "model": body.model, "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "meta": meta}

@app.get("/api/public-config")
def public_config():
    return {
        "supabase_url": os.getenv("SUPABASE_URL", ""),
        "supabase_publishable_key": os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
        "api_base_url": os.getenv("AURA_API_BASE_URL", ""),
    }

@app.get("/api/config")
def config():
    return {"name": "Aura", "version": "0.1.0", "base_model": None, "pretrained_weights": False, "architecture": MODEL.__dict__, "resource_limits": TRAINING}
