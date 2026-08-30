from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "PawGuard API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://pawguard:change-me-for-local-development@localhost:5432/pawguard"
    cors_origins: str = "http://localhost:3000"
    secret_key: str = "replace-with-a-long-random-secret-in-production"
    access_token_expire_minutes: int = 10080
    cookie_secure: bool = False
    fortyguard_api_key: str | None = None
    fortyguard_timeout_seconds: float = 20
    fortyguard_poll_seconds: float = 2
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: float = 20
    routing_base_url: str = "https://router.project-osrm.org"
    routing_profile: str = "foot"
    routing_timeout_seconds: float = 12

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
