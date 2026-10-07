"""Application configuration using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App identity
    app_env: str = Field(default="development")
    app_name: str = Field(default="GeoMeasure API")
    api_version: str = Field(default="0.1.0")
    secret_key: str = Field(default="insecure-dev-key-change-in-production")

    # Upload limits
    max_sync_size_mb: int = Field(default=50, ge=1, le=500)
    max_async_size_mb: int = Field(default=500, ge=1, le=5000)
    max_features: int = Field(default=10_000, ge=1)
    sync_timeout_s: int = Field(default=30, ge=5)

    # Zip / archive safety
    max_uncompressed_mb: int = Field(default=100)
    max_archive_files: int = Field(default=100)

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./geomeasure.db")

    # Auth & rate limiting
    api_keys: str = Field(default="dev-key-12345")
    rate_limit: str = Field(default="100/minute")

    # CORS
    allowed_origins: str = Field(default="*")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    @property
    def api_keys_set(self) -> frozenset[str]:
        """Return the set of valid API keys."""
        return frozenset(k.strip() for k in self.api_keys.split(",") if k.strip())

    @property
    def allowed_origins_list(self) -> list[str]:
        """Return allowed origins as a list."""
        if self.allowed_origins == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_sync_size_bytes(self) -> int:
        return self.max_sync_size_mb * 1024 * 1024

    @property
    def max_async_size_bytes(self) -> int:
        return self.max_async_size_mb * 1024 * 1024

    @property
    def max_uncompressed_bytes(self) -> int:
        return self.max_uncompressed_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
