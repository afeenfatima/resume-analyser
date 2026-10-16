"""OpenAI implementation of the resume-analysis gateway."""

from __future__ import annotations

import logging

from openai import APIError, OpenAI

from services.resume_service import (
    AIProviderError,
    InvalidAnalysisResponseError,
)

logger = logging.getLogger(__name__)


class OpenAIAnalysisGateway:
    """Adapt OpenAI chat completions to the application gateway interface."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Request a JSON response and translate provider failures safely."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
        except APIError as exc:
            logger.error(
                "OpenAI request failed (error_type=%s, request_id=%s).",
                type(exc).__name__,
                getattr(exc, "request_id", None),
            )
            raise AIProviderError(
                "The AI analysis service is temporarily unavailable."
            ) from exc

        if not response.choices:
            raise InvalidAnalysisResponseError(
                "The AI provider returned an empty response."
            )

        content = response.choices[0].message.content
        if not content:
            raise InvalidAnalysisResponseError(
                "The AI provider returned an empty response."
            )
        return content
