"""Notification service — publishes SNS email notifications."""

from __future__ import annotations

import structlog

from app.aws.clients import AWSClients
from app.aws.sns import SNSRepository
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)

_repo: SNSRepository | None = None


def _get_repo() -> SNSRepository:
    global _repo
    if _repo is None:
        settings = get_settings()
        clients = AWSClients(settings=settings)
        _repo = SNSRepository(clients=clients)
    return _repo


def notify_analysis_completed(job_id: str, project_name: str = "", duration_ms: float = 0) -> str | None:
    """Send email notification when analysis completes."""
    subject = f"Analysis Complete: {project_name or job_id}"
    message = (
        f"Analysis for job {job_id} has completed successfully.\n\n"
        f"Project: {project_name}\n"
        f"Duration: {duration_ms/1000:.1f} seconds\n\n"
        f"View results in the EMIP dashboard."
    )
    return _get_repo().publish_notification(subject=subject, message=message)


def notify_analysis_failed(job_id: str, error: str = "") -> str | None:
    """Send email notification when analysis fails."""
    subject = f"Analysis Failed: {job_id}"
    message = (
        f"Analysis for job {job_id} has failed.\n\n"
        f"Error: {error}\n\n"
        f"Please check the EMIP dashboard for details."
    )
    return _get_repo().publish_notification(subject=subject, message=message)
