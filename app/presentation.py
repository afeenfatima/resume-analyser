"""Reusable Streamlit rendering for resume analysis results."""

from __future__ import annotations

import streamlit as st

from .services.resume_service import ResumeAnalysis


def _render_list(title: str, values: tuple[str, ...]) -> None:
    """Render a list of analysis findings as plain text."""
    st.subheader(title)
    if values:
        for value in values:
            st.text(f"- {value}")
    else:
        st.caption("No items identified.")


def render_analysis(result: ResumeAnalysis) -> None:
    """Display all analysis fields in a consistent layout."""
    st.subheader("Resume Summary")
    st.text(result.summary)

    _render_list("Technical Skills", result.technical_skills)
    _render_list("Soft Skills", result.soft_skills)

    st.subheader("Experience Assessment")
    st.text(result.experience_assessment)

    _render_list("Suggested Job Roles", result.job_recommendations)
    st.caption(
        "These are role ideas based on the resume, not verified or live job listings."
    )
    _render_list("Skills Not Evidenced in This Resume", result.missing_skills)
    _render_list("Learning Suggestions", result.learning_suggestions)
    _render_list("Resume Improvements", result.resume_improvements)
