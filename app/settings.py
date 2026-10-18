import os


def _parse_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


class Settings:
    """Environment-backed runtime settings; no external model provider is used."""

    def __init__(self) -> None:
        self.environment = os.getenv("AURA_ENVIRONMENT", "development")
        self.cors_origins = _parse_origins(
            os.getenv("AURA_CORS_ORIGINS", "http://localhost:3000,https://aura.koharu.live")
        )
        self.checkpoint_path = os.getenv("AURA_CHECKPOINT_PATH", "models/checkpoints/aura-small.pt")


settings = Settings()
