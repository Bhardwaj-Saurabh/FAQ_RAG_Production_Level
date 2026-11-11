"""Typed application settings, read from environment variables (and `.env` in dev).

Each service gets its own group with its own env prefix, so `OPENAI_API_KEY`
fills `settings.openai.api_key` and `QDRANT_URL` fills `settings.qdrant.url`.
Groups for Redis and Postgres are added in the phases that introduce them.

Settings are built once by `get_settings()` rather than at import time
(v1 did `settings = Settings()` at module level), so a missing value fails
at startup with a clear error, and tests can build their own instance.

Where values come from, highest priority first:
  1. real environment variables (Docker, CI and cloud set these)
  2. the project's `.env` file, read only when APP_ENV is "dev" (the default)
  3. the defaults below
`.env` is found from the project root, not the current directory, and is
skipped entirely in test/prod so a stray file can never override real secrets.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvFile = Path | str | None
T = TypeVar("T", bound=BaseSettings)

# src/faq_service/config.py -> parents[2] is the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_ignore_empty=True, extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENAI_", env_ignore_empty=True, extra="ignore")

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
    model_config = SettingsConfigDict(env_prefix="QDRANT_", env_ignore_empty=True, extra="ignore")

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


def default_env_file() -> Path | None:
    """The `.env` to read: the project's in dev, none in test or prod.

    The environment is decided by the real `APP_ENV` variable, never by the
    file itself, so `.env` cannot switch itself on.
    """
    if (os.environ.get("APP_ENV") or "dev") != "dev":  # blank counts as unset
        return None
    return PROJECT_ROOT / ".env"


def load_settings(env_file: EnvFile = None) -> Settings:
    """Build settings from the environment, plus `env_file` if given."""
    return Settings(
        app=_from_env(AppSettings, env_file),
        openai=_from_env(OpenAISettings, env_file),
        qdrant=_from_env(QdrantSettings, env_file),
    )


@lru_cache
def get_settings() -> Settings:
    """The process-wide settings, built on first use."""
    return load_settings(default_env_file())
