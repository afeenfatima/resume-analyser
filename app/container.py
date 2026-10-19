"""Application composition root for Streamlit runtime dependencies."""

from __future__ import annotations

import streamlit as st


from config.settings import Settings
from infrastructure.gemini_gateway import GeminiAnalysisGateway
from services.resume_service import ResumeAnalysisService


@st.cache_resource
def get_resume_analysis_service() -> ResumeAnalysisService:
    """Create one thread-safe analysis service per Streamlit process.

    Configuration is read once when the resource is first requested. Restart
    the app process after changing provider credentials or model settings.
    """
    settings = Settings.from_env()
    
    return ResumeAnalysisService(
        gateway=GeminiAnalysisGateway(
             settings.gemini_api_key,
             settings.gemini_model,
),
        max_resume_characters=settings.max_resume_characters,
    )
