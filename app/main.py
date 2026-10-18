from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.settings import settings

app = FastAPI(
    title="Aura AI API",
    version="0.1.0",
    description="Versioned API foundation for Aura AI.",
)

# Configure explicit production origins via AURA_CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    """Return process liveness without exposing internal configuration."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": "Aura AI API", "docs": "/docs"}
