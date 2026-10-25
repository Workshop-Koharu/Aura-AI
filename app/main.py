from __future__ import annotations

import asyncio
import json
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.settings import settings
from aura.inference import AuraModelNotReady, generate_reply, model_ready

app = FastAPI(
    title="Aura AI API",
    version="0.4.0",
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


def _reply(messages: list[dict[str, str]]) -> str:
    return generate_reply(messages)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "model_ready": model_ready(),
        "model_type": "aura-transformer-from-scratch",
        "progress_stream": True,
        "reasoning_policy": "progress-only; private chain-of-thought is not exposed",
    }


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": "Aura AI API", "docs": "/docs", "model": "AuraTransformer"}


@app.post("/v1/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    if not model_ready():
        raise HTTPException(status_code=503, detail="Aura 자체 모델이 서버에서 준비되지 않았습니다.")
    try:
        result = await run_in_threadpool(_reply, [m.model_dump() for m in request.messages])
        return ChatResponse(reply=result)
    except AuraModelNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/chat/stream", tags=["chat"])
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """SSE progress/status stream. Emits user-facing progress, never private chain-of-thought."""
    if not model_ready():
        raise HTTPException(status_code=503, detail="Aura 자체 모델이 서버에서 준비되지 않았습니다.")

    async def events():
        def event(name: str, **payload: str) -> str:
            return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        yield event("progress", stage="received", message="요청을 확인했어요.")
        await asyncio.sleep(0)
        yield event("progress", stage="preparing", message="대화 문맥과 모델 상태를 확인하고 있어요.")
        await asyncio.sleep(0)
        yield event("progress", stage="generating", message="자체 Transformer가 답변을 생성하고 있어요.")
        try:
            answer = await run_in_threadpool(_reply, [m.model_dump() for m in request.messages])
        except AuraModelNotReady as exc:
            yield event("error", message=str(exc))
            return
        yield event("complete", reply=answer, message="답변 생성이 완료됐어요.")

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
