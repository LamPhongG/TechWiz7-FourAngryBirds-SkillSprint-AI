"""Application settings loaded from environment variables (and `backend/.env` in development)."""
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SkillSprint AI API"
    environment: str = "development"

    # SQLite for local work; point this at PostgreSQL (postgresql+psycopg://...) when deploying.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'skillsprint.db').as_posix()}"

    # No default on purpose: a guessable secret would let anyone mint tokens.
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 8 * 60

    # Comma-separated in .env (NoDecode skips JSON parsing); the Vite dev server runs on :3000.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    upload_dir: Path = BACKEND_DIR / "uploads"
    max_upload_mb: int = 20

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    # Tried in order when the model above is retired (404) or out of quota (429; quotas are per model). Google's
    # "-latest" aliases follow the current generation, so this list does not go stale when versions are retired.
    gemini_fallback_models: str = "gemini-flash-lite-latest,gemini-flash-latest"
    gemini_timeout_s: int = 120
    # Modules are generated in parallel; keep this under the API key's requests-per-minute quota.
    generation_workers: int = 4
    prompt_version: str = "v1.1"

    # New-account and CV-onboarding emails; without SMTP the account is still created and HR/Admin
    # is shown the temporary password to hand over another way.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_name: str = "SkillSprint AI"
    # Base of the links in invitation emails, without a trailing slash.
    frontend_url: str = "http://localhost:3000"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
