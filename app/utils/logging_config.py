"""Privacy-conscious application logging configuration."""

from __future__ import annotations

import logging
import traceback


def configure_logging() -> None:
    """Configure concise application logging without sensitive user content."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_unexpected_error(
    logger: logging.Logger,
    error: Exception,
    correlation_id: str,
) -> None:
    """Log failure context and traceback locations without exception messages."""
    frames = traceback.extract_tb(error.__traceback__)
    stack = " <- ".join(
        f"{frame.filename}:{frame.lineno}:{frame.name}" for frame in frames
    )
    logger.error(
        "Unexpected application failure (correlation_id=%s, error_type=%s, "
        "stack=%s).",
        correlation_id,
        type(error).__name__,
        stack or "unavailable",
    )
