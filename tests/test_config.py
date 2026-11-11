"""Settings come from the environment, fail loudly when required, and hide secrets.

Every test passes `env_file=None` so the developer's real `.env` never
leaks into the result.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from faq_service.config import PROJECT_ROOT, default_env_file, load_settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [
        "APP_ENV",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL_SIMPLE",
        "QDRANT_URL",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_missing_api_key_fails_at_load() -> None:
    with pytest.raises(ValidationError, match="api_key"):
        load_settings(env_file=None)


def test_values_come_from_prefixed_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL_SIMPLE", "gpt-test-mini")
    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")

    s = load_settings(env_file=None)

    assert s.openai.api_key.get_secret_value() == "sk-test"
    assert s.openai.model_simple == "gpt-test-mini"
    assert s.qdrant.url == "http://qdrant:6333"
    assert s.app.env == "dev"  # default


def test_api_key_is_hidden_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-very-secret")
    assert "sk-very-secret" not in repr(load_settings(env_file=None))


def test_blank_base_url_becomes_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "  ")
    assert load_settings(env_file=None).openai.base_url is None


def test_reads_values_from_an_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-file\nAPP_ENV=prod\n")

    s = load_settings(env_file=env_file)

    assert s.openai.api_key.get_secret_value() == "sk-from-file"
    assert s.app.env == "prod"


def test_project_root_is_the_repo_root() -> None:
    assert (PROJECT_ROOT / "pyproject.toml").is_file()


def test_dev_reads_the_project_env_file_from_any_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)  # run from somewhere else entirely
    assert default_env_file() == PROJECT_ROOT / ".env"


@pytest.mark.parametrize("env", ["test", "prod"])
def test_env_file_is_skipped_outside_dev(monkeypatch: pytest.MonkeyPatch, env: str) -> None:
    monkeypatch.setenv("APP_ENV", env)
    assert default_env_file() is None


def test_blank_app_env_counts_as_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "")  # e.g. `APP_ENV=` in a compose file
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert default_env_file() == PROJECT_ROOT / ".env"
    assert load_settings(env_file=None).app.env == "dev"
