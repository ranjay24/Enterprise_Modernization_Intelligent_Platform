"""Application startup and lifecycle management."""

import logging
import os

from app.core.settings import get_settings
from app.monitoring.logging import configure_structured_logging

logger = logging.getLogger(__name__)


def on_startup() -> None:
    """Execute on application startup."""
    configure_structured_logging()
    logger.info("EMIP backend starting", extra={"version": "1.0.0"})
    _validate_aws_config()


def _validate_aws_config() -> None:
    """Fail fast (locally) when AWS resource settings still point at the
    non-existent placeholder defaults, instead of surfacing later as
    NoSuchBucket / ResourceNotFoundException during a request."""
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return  # Lambda receives real values from the SAM template
    settings = get_settings()
    problems = settings.aws_config_problems
    if not problems:
        return
    raise RuntimeError(
        "EMIP AWS configuration is incomplete — refusing to start.\n"
        + "\n".join(f"  - {p}" for p in problems)
        + "\nCopy backend/.env.example to backend/.env and fill in real resource "
        "names (see SETUP.md), or set the environment variables above."
    )


def on_shutdown() -> None:
    """Execute on application shutdown."""
    logger.info("EMIP backend shutting down")
