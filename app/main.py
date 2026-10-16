"""Streamlit entry point for the AI Resume Analyzer."""

from __future__ import annotations

import logging
from uuid import uuid4

import streamlit as st

from app.container import get_resume_analysis_service
from app.config.settings import ConfigurationError, Settings
from app.presentation import render_analysis
from app.services.resume_service import (
    AIProviderError,
    InvalidAnalysisResponseError,
    InvalidResumeError,
)
from app.utils.logging_config import configure_logging, log_unexpected_error

logger = logging.getLogger(__name__)


def _clear_analysis_result() -> None:
    """Discard an earlier result when the resume text changes."""
    st.session_state.pop("analysis_result", None)


def main() -> None:
    """Render the Streamlit interface and handle user-safe failures."""
    configure_logging()
    st.set_page_config(page_title="AI Resume Analyzer", page_icon="📝")
    st.title("AI Resume Analyzer")
    st.write(
        "Get structured, AI-generated feedback to support your career planning."
    )
    st.info(
        "Your resume text is sent to the configured AI provider for analysis. "
        "Results may be incomplete or incorrect; review them before relying on "
        "them. This tool does not make hiring decisions."
    )

    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        logger.error("Application configuration is invalid: %s", exc)
        st.error(
            "The application is not configured. Set OPENAI_API_KEY in your "
            "environment or .env file, then restart the app."
        )
        st.stop()
        return

    resume_text = st.text_area(
        "Paste your resume text",
        height=320,
        max_chars=settings.max_resume_characters,
        placeholder="Paste the text from your resume here...",
        on_change=_clear_analysis_result,
    )
    consent_given = st.checkbox(
        "I understand my resume text will be sent to the configured AI provider "
        "for analysis."
    )

    if st.button("Analyze Resume", type="primary"):
        if not consent_given:
            st.warning("Please confirm the data-processing notice before continuing.")
            return
        correlation_id = uuid4().hex
        st.session_state.pop("analysis_result", None)
        try:
            with st.spinner("Analyzing your resume..."):
                result = get_resume_analysis_service().analyze(resume_text)
            st.session_state["analysis_result"] = result
            st.success("Analysis complete.")
        except InvalidResumeError as exc:
            st.warning(str(exc))
        except AIProviderError:
            st.error(
                "Resume analysis could not be completed right now. Please try "
                "again later."
            )
        except InvalidAnalysisResponseError:
            st.error(
                "The analysis response could not be validated. Please try again."
            )
        except Exception as exc:
            log_unexpected_error(logger, exc, correlation_id)
            st.error(
                "An unexpected error prevented analysis. Please try again; "
                f"contact support with reference {correlation_id} if the problem "
                "continues."
            )

    analysis_result = st.session_state.get("analysis_result")
    if analysis_result is not None:
        render_analysis(analysis_result)


if __name__ == "__main__":
    main()
