"""Application configuration loaded from environment variables / .env file."""
import json
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings. Overridable via a `.env` file or env vars."""

    APP_NAME: str = "News Discovery & Management API"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    DATABASE_URL: str = "sqlite:///./news.db"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS (comma-separated or JSON list in .env)
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # External news discovery (optional)
    NEWS_API_KEY: str | None = None
    NEWS_API_BASE_URL: str = "https://newsapi.org/v2"

    # Scheduled auto-discovery (only active when NEWS_API_KEY is set)
    NEWS_AUTO_FETCH: bool = False
    NEWS_FETCH_INTERVAL_MINUTES: int = 60
    NEWS_COUNTRY: str = "us"
    NEWS_AUTO_CATEGORIES: Annotated[list[str], NoDecode] = [
        "technology",
        "business",
        "science",
        "health",
        "sports",
        "entertainment",
    ]

    # Behaviour
    SEED_ON_STARTUP: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", "NEWS_AUTO_CATEGORIES", mode="before")
    @classmethod
    def _parse_csv_list(cls, value):
        """Accept either a JSON list or a simple comma-separated string."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
