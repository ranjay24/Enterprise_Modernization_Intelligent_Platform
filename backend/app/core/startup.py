"""Application startup and lifecycle management."""

import logging

from app.monitoring.logging import configure_structured_logging

logger = logging.getLogger(__name__)


def on_startup() -> None:
    """Execute on application startup."""
    configure_structured_logging()
    logger.info("EMIP backend starting", extra={"version": "1.0.0"})


def on_shutdown() -> None:
    """Execute on application shutdown."""
    logger.info("EMIP backend shutting down")
