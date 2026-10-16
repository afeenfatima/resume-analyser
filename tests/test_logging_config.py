"""Tests for privacy-safe error logging."""

from __future__ import annotations

import logging

import pytest

from utils.logging_config import log_unexpected_error


def test_unexpected_error_log_omits_exception_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Trace locations are logged without potentially sensitive error text."""
    logger = logging.getLogger("test.safe_logging")

    try:
        raise RuntimeError("private resume text")
    except RuntimeError as error:
        with caplog.at_level(logging.ERROR, logger=logger.name):
            log_unexpected_error(logger, error, "analysis-123")

    assert "analysis-123" in caplog.text
    assert "RuntimeError" in caplog.text
    assert "private resume text" not in caplog.text
