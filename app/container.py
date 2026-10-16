"""Application composition root for Streamlit runtime dependencies."""

from __future__ import annotations

import streamlit as st
from openai import OpenAI

from app.config.settings import Settings
from app.infrastructure.openai_gateway import OpenAIAnalysisGateway
from app.services.resume_service import ResumeAnalysisService


@st.cache_resource
def get_resume_analysis_service() -> ResumeAnalysisService:
    """Create one thread-safe analysis service per Streamlit process.

    Configuration is read once when the resource is first requested. Restart
    the app process after changing provider credentials or model settings.
    """
    settings = Settings.from_env()
    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=2,
    )
    return ResumeAnalysisService(
        gateway=OpenAIAnalysisGateway(client, settings.openai_model),
        max_resume_characters=settings.max_resume_characters,
    )
