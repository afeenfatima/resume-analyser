"""Unit and validation tests for application settings."""

from __future__ import annotations

import pytest

from config import settings as settings_module
from config.settings import ConfigurationError, Settings


@pytest.fixture(autouse=True)
def isolate_settings_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prevent developer .env files or ambient variables affecting test results."""
    monkeypatch.setattr(settings_module, "load_dotenv", lambda: None)
    for variable in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_TIMEOUT_SECONDS",
        "MAX_RESUME_CHARACTERS",
    ):
        monkeypatch.delenv(variable, raising=False)


def test_settings_load_defaults_with_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required API key is accepted while optional fields use documented defaults."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")

    settings = Settings.from_env()

    assert settings == Settings(openai_api_key="test-only-key")
    assert settings.openai_model == "gpt-4o-mini"
    assert settings.openai_timeout_seconds == 45.0
    assert settings.max_resume_characters == 30_000


def test_settings_load_explicit_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured values are parsed and surrounding whitespace is stripped."""
    monkeypatch.setenv("OPENAI_API_KEY", "  test-only-key  ")
    monkeypatch.setenv("OPENAI_MODEL", "  test-model  ")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("MAX_RESUME_CHARACTERS", "5000")

    settings = Settings.from_env()

    assert settings.openai_api_key == "test-only-key"
    assert settings.openai_model == "test-model"
    assert settings.openai_timeout_seconds == 12.5
    assert settings.max_resume_characters == 5_000


@pytest.mark.parametrize("api_key", ["", " ", "\t"])
def test_settings_reject_missing_or_blank_api_key(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str,
) -> None:
    """A missing or whitespace-only API key fails before application startup."""
    monkeypatch.setenv("OPENAI_API_KEY", api_key)

    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY is required"):
        Settings.from_env()


@pytest.mark.parametrize("model", ["", " ", "\t"])
def test_settings_reject_blank_model(
    monkeypatch: pytest.MonkeyPatch,
    model: str,
) -> None:
    """An explicitly blank model name is not silently accepted."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENAI_MODEL", model)

    with pytest.raises(ConfigurationError, match="OPENAI_MODEL must not be empty"):
        Settings.from_env()


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("OPENAI_TIMEOUT_SECONDS", "invalid"),
        ("MAX_RESUME_CHARACTERS", "invalid"),
    ],
)
def test_settings_reject_non_numeric_values(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    value: str,
) -> None:
    """Malformed numeric configuration is reported as a configuration error."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv(variable, value)

    with pytest.raises(ConfigurationError, match="must be numeric"):
        Settings.from_env()


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf", "-inf"])
def test_settings_reject_non_positive_or_non_finite_timeout(
    monkeypatch: pytest.MonkeyPatch,
    timeout: str,
) -> None:
    """Timeout must be a finite positive number."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", timeout)

    with pytest.raises(
        ConfigurationError,
        match="finite number greater than 0",
    ):
        Settings.from_env()


@pytest.mark.parametrize("limit", ["0", "-1"])
def test_settings_reject_non_positive_resume_limit(
    monkeypatch: pytest.MonkeyPatch,
    limit: str,
) -> None:
    """Resume limits must be positive integers."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("MAX_RESUME_CHARACTERS", limit)

    with pytest.raises(
        ConfigurationError,
        match="MAX_RESUME_CHARACTERS must be greater than 0",
    ):
        Settings.from_env()
