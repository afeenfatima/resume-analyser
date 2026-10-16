"""Tests for the OpenAI analysis adapter."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from openai import APIError

from app.infrastructure.openai_gateway import OpenAIAnalysisGateway
from app.services.resume_service import (
    AIProviderError,
    InvalidAnalysisResponseError,
)


def make_client(response: object) -> Mock:
    """Create a mock client with a configured completion response."""
    client = Mock()
    client.chat.completions.create.return_value = response
    return client


def test_gateway_returns_completion_text() -> None:
    """The adapter extracts content from the first provider choice."""
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"ok"}'))]
    )
    client = make_client(response)
    gateway = OpenAIAnalysisGateway(client, "test-model")

    result = gateway.complete("system", "user")

    assert result == '{"summary":"ok"}'
    client.chat.completions.create.assert_called_once()


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None))]),
    ],
)
def test_gateway_rejects_empty_completion(response: object) -> None:
    """Missing choices or empty content is surfaced as a typed error."""
    gateway = OpenAIAnalysisGateway(make_client(response), "test-model")

    with pytest.raises(InvalidAnalysisResponseError, match="empty response"):
        gateway.complete("system", "user")


def test_gateway_translates_provider_error_without_logging_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Provider errors are typed and sensitive exception text is not logged."""
    client = Mock()
    client.chat.completions.create.side_effect = APIError(
        "sensitive provider detail",
        request=Mock(),
        body=None,
    )
    gateway = OpenAIAnalysisGateway(client, "test-model")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(AIProviderError):
            gateway.complete("system", "user")

    assert "sensitive provider detail" not in caplog.text
    assert "APIError" in caplog.text
