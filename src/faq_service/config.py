"""Typed application settings, read from environment variables and `.env`.

Each service gets its own group with its own env prefix, so `OPENAI_API_KEY`
fills `settings.openai.api_key` and `QDRANT_URL` fills `settings.qdrant.url`.
Groups for Redis and Postgres are added in the phases that introduce them.

Settings are built once by `get_settings()` rather than at import time
(v1 did `settings = Settings()` at module level), so a missing value fails
at startup with a clear error, and tests can build their own instance.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvFile = Path | str | None
T = TypeVar("T", bound=BaseSettings)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENAI_", env_file=".env", extra="ignore")

    # Required: there is no sensible default, so startup fails without it.
    # SecretStr keeps the key out of logs and reprs ("**********").
    api_key: SecretStr
    # None means the SDK default (api.openai.com). Set it for the Vocareum proxy.
    base_url: str | None = None
    model_simple: str = "gpt-4o-mini"
    model_complex: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    @field_validator("base_url", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        # `OPENAI_BASE_URL=` in .env arrives as "", which would point the SDK at nothing.
        if isinstance(value, str) and not value.strip():
            return None
        return value


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_", env_file=".env", extra="ignore")

    url: str = "http://localhost:6333"
    # Only needed for Qdrant Cloud; the local container has no auth.
    api_key: SecretStr | None = None
    collection: str = "products"


class Settings(BaseModel):
    app: AppSettings
    openai: OpenAISettings
    qdrant: QdrantSettings


def _from_env(group: type[T], env_file: EnvFile) -> T:
    # Typed against BaseSettings' own __init__, which accepts `_env_file`;
    # mypy only sees the field arguments on the subclasses themselves.
    return group(_env_file=env_file)


def load_settings(env_file: EnvFile = ".env") -> Settings:
    """Build settings from the environment, plus `env_file` if given (None skips it)."""
    return Settings(
        app=_from_env(AppSettings, env_file),
        openai=_from_env(OpenAISettings, env_file),
        qdrant=_from_env(QdrantSettings, env_file),
    )


@lru_cache
def get_settings() -> Settings:
    """The process-wide settings, built on first use."""
    return load_settings()
