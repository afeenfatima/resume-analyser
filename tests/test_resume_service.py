"""Unit tests for resume analysis validation and orchestration."""

from __future__ import annotations

import json

import pytest

from services.resume_service import (
    AIProviderError,
    InvalidAnalysisResponseError,
    InvalidResumeError,
    ResumeAnalysis,
    ResumeAnalysisService,
)


class FakeGateway:
    """Test gateway returning a fixed provider response."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.last_system_prompt = ""
        self.last_user_prompt = ""
        self.call_count = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.response


def valid_payload() -> dict[str, object]:
    """Return a valid analysis fixture."""
    return {
        "summary": "Backend developer with Python experience.",
        "technical_skills": ["Python", "SQL"],
        "soft_skills": ["Communication"],
        "experience_assessment": "Project evidence is present.",
        "job_recommendations": ["Junior Python Developer"],
        "missing_skills": ["Cloud deployment is not evidenced."],
        "learning_suggestions": ["Explore a cloud fundamentals course."],
        "resume_improvements": ["Add measurable project outcomes if available."],
    }


def test_analyze_returns_validated_analysis() -> None:
    """A valid provider response is returned as an immutable model."""
    gateway = FakeGateway(json.dumps(valid_payload()))
    service = ResumeAnalysisService(gateway, max_resume_characters=1_000)

    result = service.analyze("  Resume content  ")

    assert isinstance(result, ResumeAnalysis)
    assert result.technical_skills == ("Python", "SQL")
    assert "untrusted data" in gateway.last_system_prompt
    assert '"Resume content"' in gateway.last_user_prompt


def test_analyze_normalizes_resume_text_before_sending() -> None:
    """Leading/trailing whitespace is removed before constructing the prompt."""
    gateway = FakeGateway(json.dumps(valid_payload()))
    service = ResumeAnalysisService(gateway, max_resume_characters=100)

    service.analyze(" \nResume body\t ")

    assert '"Resume body"' in gateway.last_user_prompt
    assert gateway.call_count == 1


def test_analyze_accepts_resume_at_exact_character_limit() -> None:
    """The configured character limit is inclusive."""
    gateway = FakeGateway(json.dumps(valid_payload()))
    service = ResumeAnalysisService(gateway, max_resume_characters=4)

    result = service.analyze("test")

    assert result.summary == "Backend developer with Python experience."
    assert gateway.call_count == 1


@pytest.mark.parametrize("resume_text", ["", "  ", "\n"])
def test_analyze_rejects_empty_resume(resume_text: str) -> None:
    """Empty resume input fails before calling the provider."""
    gateway = FakeGateway(json.dumps(valid_payload()))
    service = ResumeAnalysisService(
        gateway,
        max_resume_characters=100,
    )

    with pytest.raises(InvalidResumeError, match="Paste resume text"):
        service.analyze(resume_text)
    assert gateway.call_count == 0


def test_analyze_rejects_resume_over_limit() -> None:
    """Resume character limits are enforced before provider calls."""
    gateway = FakeGateway(json.dumps(valid_payload()))
    service = ResumeAnalysisService(
        gateway,
        max_resume_characters=4,
    )

    with pytest.raises(InvalidResumeError, match="character limit"):
        service.analyze("12345")
    assert gateway.call_count == 0


def test_service_rejects_non_positive_character_limit() -> None:
    """A service cannot be configured with an unusable resume limit."""
    with pytest.raises(ValueError, match="must be greater than 0"):
        ResumeAnalysisService(FakeGateway("{}"), max_resume_characters=0)


@pytest.mark.parametrize("response", ["null", "[]", '"text"', "1", "true"])
def test_analysis_rejects_non_object_json(response: str) -> None:
    """Valid JSON with a non-object top-level value is invalid analysis."""
    service = ResumeAnalysisService(
        FakeGateway(response),
        max_resume_characters=1_000,
    )

    with pytest.raises(InvalidAnalysisResponseError, match="JSON object"):
        service.analyze("Resume content")


def test_analysis_rejects_unexpected_response_fields() -> None:
    """Unexpected provider fields do not leak into the application model."""
    payload = valid_payload()
    payload["extra"] = "not allowed"
    service = ResumeAnalysisService(
        FakeGateway(json.dumps(payload)),
        max_resume_characters=1_000,
    )

    with pytest.raises(InvalidAnalysisResponseError, match="expected fields"):
        service.analyze("Resume content")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("summary", "", "invalid summary"),
        ("summary", 42, "invalid summary"),
        ("experience_assessment", [], "invalid experience_assessment"),
        ("technical_skills", "Python", "invalid technical_skills list"),
        ("soft_skills", [" "], "invalid item in soft_skills"),
        ("job_recommendations", [42], "invalid item in job_recommendations"),
    ],
)
def test_analysis_rejects_invalid_field_values(
    field: str,
    value: object,
    message: str,
) -> None:
    """Wrong field types and empty values fail validation."""
    payload = valid_payload()
    payload[field] = value
    service = ResumeAnalysisService(
        FakeGateway(json.dumps(payload)),
        max_resume_characters=1_000,
    )

    with pytest.raises(InvalidAnalysisResponseError, match=message):
        service.analyze("Resume content")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("summary", "x" * 2_001, "oversized summary"),
        ("learning_suggestions", ["x" * 2_001], "invalid item"),
        ("resume_improvements", ["item"] * 21, "invalid resume_improvements list"),
    ],
)
def test_analysis_rejects_oversized_response_values(
    field: str,
    value: object,
    message: str,
) -> None:
    """Response size and item-count caps are enforced."""
    payload = valid_payload()
    payload[field] = value
    service = ResumeAnalysisService(
        FakeGateway(json.dumps(payload)),
        max_resume_characters=1_000,
    )

    with pytest.raises(InvalidAnalysisResponseError, match=message):
        service.analyze("Resume content")


def test_analysis_accepts_empty_result_lists() -> None:
    """A valid response may have no findings in any list category."""
    payload = valid_payload()
    for field in (
        "technical_skills",
        "soft_skills",
        "job_recommendations",
        "missing_skills",
        "learning_suggestions",
        "resume_improvements",
    ):
        payload[field] = []
    service = ResumeAnalysisService(
        FakeGateway(json.dumps(payload)),
        max_resume_characters=1_000,
    )

    result = service.analyze("Resume content")

    assert result.technical_skills == ()
    assert result.job_recommendations == ()


def test_analysis_rejects_malformed_json() -> None:
    """Malformed JSON is translated to a typed application error."""
    service = ResumeAnalysisService(
        FakeGateway("{not-json"),
        max_resume_characters=1_000,
    )

    with pytest.raises(InvalidAnalysisResponseError, match="malformed JSON"):
        service.analyze("Resume content")


def test_service_propagates_typed_provider_error() -> None:
    """Provider errors reach the caller without success-shaped fallback data."""

    class FailingGateway:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            assert system_prompt
            assert user_prompt
            raise AIProviderError("provider unavailable")

    service = ResumeAnalysisService(
        FailingGateway(),
        max_resume_characters=1_000,
    )

    with pytest.raises(AIProviderError, match="provider unavailable"):
        service.analyze("Resume content")
