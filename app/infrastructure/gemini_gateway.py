from __future__ import annotations

import logging

import google.generativeai as genai

from services.resume_service import (
    AIProviderError,
    InvalidAnalysisResponseError,
)

logger = logging.getLogger(__name__)


class GeminiAnalysisGateway:
    def __init__(self, api_key: str, model: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._model.generate_content(
                f"{system_prompt}\n\n{user_prompt}"
            )
        except Exception as exc:
            logger.exception("Gemini request failed")
            raise AIProviderError(
                "The AI analysis service is temporarily unavailable."
            ) from exc

        if not response.text:
            raise InvalidAnalysisResponseError(
                "The AI provider returned an empty response."
            )

        return response.text