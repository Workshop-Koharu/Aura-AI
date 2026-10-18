from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.settings import settings

app = FastAPI(
    title="Aura AI API",
    version="0.2.0",
    description="Aura AI API for health checks and chat.",
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
def health() -> dict[str, str]:
    """Return process liveness without exposing internal configuration."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": "Aura AI API", "docs": "/docs"}


@app.post("/v1/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    """Forward a bounded conversation to the configured OpenAI-compatible provider."""
    if not settings.model_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI 모델이 아직 설정되지 않았습니다. Render 환경 변수에 "
                "AURA_MODEL_API_KEY를 추가하고 서비스를 재배포하세요."
            ),
        )

    payload = {
        "model": settings.model_name,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Aura AI, a clear, careful, helpful assistant. "
                    "Respond in the user's language. Be accurate and acknowledge uncertainty."
                ),
            },
            *[message.model_dump() for message in request.messages],
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
            response = await client.post(
                settings.model_base_url + "/chat/completions",
                headers={
                    "Authorization": "Bearer " + settings.model_api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            reply = result["choices"][0]["message"]["content"]
            if not isinstance(reply, str) or not reply.strip():
                raise ValueError("Provider returned an empty message.")
            return ChatResponse(reply=reply.strip())
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도하세요.") from exc
    except httpx.HTTPStatusError as exc:
        # Do not expose upstream response bodies, which can contain provider diagnostics.
        raise HTTPException(
            status_code=502,
            detail="AI 모델 제공자 요청이 실패했습니다. Render 로그와 모델 설정을 확인하세요.",
        ) from exc
    except (httpx.RequestError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="AI 모델 응답을 처리하지 못했습니다. 모델 제공자 설정을 확인하세요.",
        ) from exc
