"""Resume analysis use case and validated result models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from app.prompts.resume_prompt import SYSTEM_PROMPT, build_resume_prompt

_TEXT_FIELDS = ("summary", "experience_assessment")
_LIST_FIELDS = (
    "technical_skills",
    "soft_skills",
    "job_recommendations",
    "missing_skills",
    "learning_suggestions",
    "resume_improvements",
)
_EXPECTED_FIELDS = frozenset((*_TEXT_FIELDS, *_LIST_FIELDS))
_MAX_FIELD_LENGTH = 2_000
_MAX_LIST_ITEMS = 20


class ResumeAnalysisError(Exception):
    """Base exception for expected resume analysis failures."""


class InvalidResumeError(ResumeAnalysisError):
    """Raised when submitted resume text is invalid or exceeds configured limits."""


class AIProviderError(ResumeAnalysisError):
    """Raised when the configured AI provider cannot complete the request."""


class InvalidAnalysisResponseError(ResumeAnalysisError):
    """Raised when the AI response cannot be parsed or fails validation."""


class AnalysisGateway(Protocol):
    """Port implemented by the configured AI provider adapter."""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return the provider's textual response."""


@dataclass(frozen=True, slots=True)
class ResumeAnalysis:
    """Validated resume analysis returned to the presentation layer."""

    summary: str
    technical_skills: tuple[str, ...]
    soft_skills: tuple[str, ...]
    experience_assessment: str
    job_recommendations: tuple[str, ...]
    missing_skills: tuple[str, ...]
    learning_suggestions: tuple[str, ...]
    resume_improvements: tuple[str, ...]

    @classmethod
    def from_json(cls, response_text: str) -> "ResumeAnalysis":
        """Parse and validate a JSON response against the public result shape."""
        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise InvalidAnalysisResponseError(
                "The AI provider returned malformed JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise InvalidAnalysisResponseError(
                "The AI provider response must be a JSON object."
            )
        if set(payload) != _EXPECTED_FIELDS:
            raise InvalidAnalysisResponseError(
                "The AI provider response did not contain the expected fields."
            )

        validated_text: dict[str, str] = {}
        validated_lists: dict[str, tuple[str, ...]] = {}
        for field in _TEXT_FIELDS:
            value = payload[field]
            if not isinstance(value, str) or not value.strip():
                raise InvalidAnalysisResponseError(
                    f"The AI provider returned an invalid {field} value."
                )
            if len(value) > _MAX_FIELD_LENGTH:
                raise InvalidAnalysisResponseError(
                    f"The AI provider returned an oversized {field} value."
                )
            validated_text[field] = value.strip()

        for field in _LIST_FIELDS:
            value = payload[field]
            if not isinstance(value, list) or len(value) > _MAX_LIST_ITEMS:
                raise InvalidAnalysisResponseError(
                    f"The AI provider returned an invalid {field} list."
                )
            items: list[str] = []
            for item in value:
                if (
                    not isinstance(item, str)
                    or not item.strip()
                    or len(item) > _MAX_FIELD_LENGTH
                ):
                    raise InvalidAnalysisResponseError(
                        f"The AI provider returned an invalid item in {field}."
                    )
                items.append(item.strip())
            validated_lists[field] = tuple(items)

        return cls(
            summary=validated_text["summary"],
            technical_skills=validated_lists["technical_skills"],
            soft_skills=validated_lists["soft_skills"],
            experience_assessment=validated_text["experience_assessment"],
            job_recommendations=validated_lists["job_recommendations"],
            missing_skills=validated_lists["missing_skills"],
            learning_suggestions=validated_lists["learning_suggestions"],
            resume_improvements=validated_lists["resume_improvements"],
        )


class ResumeAnalysisService:
    """Validate resume text and request a safe, structured AI analysis."""

    def __init__(
        self,
        gateway: AnalysisGateway,
        max_resume_characters: int,
    ) -> None:
        if max_resume_characters <= 0:
            raise ValueError("max_resume_characters must be greater than 0.")
        self._gateway = gateway
        self._max_resume_characters = max_resume_characters

    def analyze(self, resume_text: str) -> ResumeAnalysis:
        """Analyze non-empty resume text without logging its contents."""
        if not isinstance(resume_text, str) or not resume_text.strip():
            raise InvalidResumeError("Paste resume text before submitting.")
        if len(resume_text) > self._max_resume_characters:
            raise InvalidResumeError(
                "The resume exceeds the configured character limit "
                f"({self._max_resume_characters:,})."
            )

        response = self._gateway.complete(
            SYSTEM_PROMPT,
            build_resume_prompt(resume_text.strip()),
        )
        return ResumeAnalysis.from_json(response)
