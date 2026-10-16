"""Streamlit interaction tests using a stubbed analysis service."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from app import main
from config.settings import Settings
from services.resume_service import ResumeAnalysis


class FakeAnalysisService:
    """In-memory service stub for the Streamlit workflow."""

    def __init__(self) -> None:
        self.submitted_resumes: list[str] = []

    def analyze(self, resume_text: str) -> ResumeAnalysis:
        self.submitted_resumes.append(resume_text)
        return ResumeAnalysis(
            summary="Test summary",
            technical_skills=("Python",),
            soft_skills=("Communication",),
            experience_assessment="Project experience is described.",
            job_recommendations=("Junior Python Developer",),
            missing_skills=("Cloud skills are not evidenced.",),
            learning_suggestions=("Review cloud fundamentals.",),
            resume_improvements=("Clarify project outcomes.",),
        )


def configure_app(
    monkeypatch: pytest.MonkeyPatch,
    service: FakeAnalysisService,
) -> None:
    """Replace runtime settings and the external analysis dependency."""
    monkeypatch.setattr(
        main.Settings,
        "from_env",
        classmethod(lambda cls: cls(openai_api_key="test-key")),
    )
    monkeypatch.setattr(main, "get_resume_analysis_service", lambda: service)


def _run_app() -> None:
    """Import the app inside the isolated Streamlit test script."""
    from main import main as render_main

    render_main()


def test_analysis_requires_consent(monkeypatch: pytest.MonkeyPatch) -> None:
    """The UI does not submit resume text until the user confirms consent."""
    service = FakeAnalysisService()
    configure_app(monkeypatch, service)
    app = AppTest.from_function(_run_app).run()

    text_area[0].set_value("Example resume")
    button[0].click().run()

    assert service.submitted_resumes == []
    assert "Please confirm the data-processing notice before continuing." in [
        element.value for element in warning
    ]


def test_analysis_result_persists_until_resume_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A completed result survives reruns and clears when resume text changes."""
    service = FakeAnalysisService()
    configure_app(monkeypatch, service)
    app = AppTest.from_function(_run_app).run()

    text_area[0].set_value("Example resume")
    checkbox[0].check()
    button[0].click().run()

    assert service.submitted_resumes == ["Example resume"]
    assert session_state["analysis_result"].summary == "Test summary"

    run()
    assert session_state["analysis_result"].summary == "Test summary"

    text_area[0].set_value("Updated resume").run()
    assert "analysis_result" not in session_state
