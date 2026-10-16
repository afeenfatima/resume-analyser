"""Validated environment-based application settings."""

from __future__ import annotations

import os
import math
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when required application configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: float = 45.0
    max_resume_characters: int = 30_000

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from the environment and an optional local .env file."""
        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required. Add it to your environment or .env file."
            )

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        if not model:
            raise ConfigurationError("OPENAI_MODEL must not be empty.")

        timeout_value = os.getenv("OPENAI_TIMEOUT_SECONDS", "45")
        max_resume_value = os.getenv("MAX_RESUME_CHARACTERS", "30000")
        try:
            timeout = float(timeout_value)
            max_resume_characters = int(max_resume_value)
        except ValueError as exc:
            raise ConfigurationError(
                "OPENAI_TIMEOUT_SECONDS and MAX_RESUME_CHARACTERS must be numeric."
            ) from exc

        if not math.isfinite(timeout) or timeout <= 0:
            raise ConfigurationError(
                "OPENAI_TIMEOUT_SECONDS must be a finite number greater than 0."
            )
        if max_resume_characters <= 0:
            raise ConfigurationError("MAX_RESUME_CHARACTERS must be greater than 0.")

        return cls(
            openai_api_key=api_key,
            openai_model=model,
            openai_timeout_seconds=timeout,
            max_resume_characters=max_resume_characters,
        )
