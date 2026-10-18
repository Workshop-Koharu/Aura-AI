import os


def _parse_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


class Settings:
    """Small environment-backed settings object; secrets are never hard-coded."""

    def __init__(self) -> None:
        self.environment = os.getenv("AURA_ENVIRONMENT", "development")
        self.cors_origins = _parse_origins(
            os.getenv("AURA_CORS_ORIGINS", "http://localhost:3000,https://aura.koharu.live")
        )
        self.model_api_key = os.getenv("AURA_MODEL_API_KEY", "").strip()
        self.model_base_url = os.getenv("AURA_MODEL_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model_name = os.getenv("AURA_MODEL_NAME", "gpt-4o-mini").strip()


settings = Settings()
