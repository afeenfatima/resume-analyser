"""Offline integration tests for service-to-OpenAI-adapter wiring."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from openai import APIError

from app.infrastructure.openai_gateway import OpenAIAnalysisGateway
from app.services.resume_service import (
    AIProviderError,
    InvalidResumeError,
    ResumeAnalysisService,
)


def analysis_response() -> dict[str, object]:
    """Return deterministic mock data for the provider contract."""
    return {
        "summary": "Early-career software developer.",
        "technical_skills": ["Python", "SQL"],
        "soft_skills": ["Collaboration"],
        "experience_assessment": "Project work demonstrates relevant experience.",
        "job_recommendations": ["Junior Software Developer"],
        "missing_skills": ["Testing is not evidenced in the resume."],
        "learning_suggestions": ["Practice writing automated tests."],
        "resume_improvements": ["Describe project outcomes more precisely."],
    }


def make_mock_openai_client(content: str) -> Mock:
    """Build an OpenAI-shaped mock client without an HTTP transport."""
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )
    return client


def test_service_integrates_with_mocked_openai_adapter() -> None:
    """A fake OpenAI response passes through adapter and service validation."""
    content = json.dumps(analysis_response())
    openai_client = make_mock_openai_client(content)
    gateway = OpenAIAnalysisGateway(openai_client, "offline-test-model")
    service = ResumeAnalysisService(gateway, max_resume_characters=2_000)

    result = service.analyze("Python developer with project experience.")

    assert result.summary == "Early-career software developer."
    assert result.technical_skills == ("Python", "SQL")
    assert result.job_recommendations == ("Junior Software Developer",)
    openai_client.chat.completions.create.assert_called_once()

    request = openai_client.chat.completions.create.call_args.kwargs
    assert request["model"] == "offline-test-model"
    assert request["response_format"] == {"type": "json_object"}
    assert request["messages"][1]["content"].endswith(
        '"Python developer with project experience."'
    )


def test_invalid_resume_does_not_call_mocked_openai() -> None:
    """Input validation happens before any provider interaction."""
    openai_client = make_mock_openai_client("{}")
    service = ResumeAnalysisService(
        OpenAIAnalysisGateway(openai_client, "offline-test-model"),
        max_resume_characters=20,
    )

    with pytest.raises(InvalidResumeError, match="Paste resume text"):
        service.analyze("  ")

    openai_client.chat.completions.create.assert_not_called()


def test_provider_failure_is_translated_and_propagated() -> None:
    """Provider failures do not produce partial or success-shaped results."""
    openai_client = Mock()
    openai_client.chat.completions.create.side_effect = APIError(
        "simulated provider outage",
        request=Mock(),
        body=None,
    )
    service = ResumeAnalysisService(
        OpenAIAnalysisGateway(openai_client, "offline-test-model"),
        max_resume_characters=2_000,
    )

    with pytest.raises(
        AIProviderError,
        match="temporarily unavailable",
    ):
        service.analyze("Resume content")

    openai_client.chat.completions.create.assert_called_once()
