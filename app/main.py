from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.settings import settings
from aura.inference import AuraModelNotReady, generate_reply, model_ready

app = FastAPI(
    title="Aura AI API",
    version="0.3.0",
    description="Aura's own from-scratch Transformer inference API.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


class ChatResponse(BaseModel):
    reply: str


@app.get("/health", tags=["operations"])
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "model_ready": model_ready(),
        "model_type": "aura-transformer-from-scratch",
    }


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": "Aura AI API", "docs": "/docs", "model": "AuraTransformer"}


@app.post("/v1/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    if not model_ready():
        raise HTTPException(
            status_code=503,
            detail="Aura 자체 모델이 아직 학습되지 않았습니다. python -m aura.train --data data/train.txt 명령으로 학습한 뒤 체크포인트를 서버에 배포하세요.",
        )
    try:
        return ChatResponse(
            reply=await run_in_threadpool(
                generate_reply, [m.model_dump() for m in request.messages]
            )
        )
    except AuraModelNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
