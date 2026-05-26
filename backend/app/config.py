"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized app settings. Loaded from .env at startup."""

    model_config = SettingsConfigDict(
        env_file="../.env",          # root-level .env
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "jarvis"
    app_env: str = "development"
    log_level: str = "INFO"
    timezone_default: str = "Asia/Ho_Chi_Minh"

    # ---- Server ----
    backend_port: int = 8000
    backend_cors_origins: str = "http://localhost:3000"

    # ---- Database ----
    database_url: str = Field(..., description="Async DB URL (asyncpg)")
    database_url_direct: str | None = Field(None, description="Sync DB URL for Alembic")

    # ---- LLM ----
    gemini_api_key: str = Field(..., description="Google AI Studio key")
    openai_api_key: str = Field(..., description="OpenAI key for fallback")
    anthropic_api_key: str | None = None

    llm_primary: str = "gemini/gemini-2.5-flash"
    llm_fallback: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 30
    llm_max_tokens_out: int = 1000

    # ---- Embedding ----
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # ---- Auth ----
    jwt_secret: str = Field(..., min_length=32)
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30

    google_client_id: str | None = None
    google_client_secret: str | None = None

    # ---- Cookie ----
    cookie_samesite: str = "lax"   # production cross-site (Vercel→Railway): set "none"
    cookie_secure: bool = False     # production HTTPS: set True
    cookie_domain: str | None = None

    # ---- Web Push ----
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:admin@example.com"

    # ---- Computed ----
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance. Use this everywhere."""
    return Settings()
