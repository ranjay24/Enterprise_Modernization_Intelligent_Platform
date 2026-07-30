"""Event publisher — publishes pipeline events to EventBridge."""

from __future__ import annotations

import structlog

from app.aws.eventbridge import EventBridgeRepository

logger = structlog.get_logger(__name__)

EVENT_SCHEMA_VERSION = "1.0.0"

_publisher: EventBridgeRepository | None = None


def _get_publisher() -> EventBridgeRepository:
    global _publisher
    if _publisher is None:
        _publisher = EventBridgeRepository()
    return _publisher


def _base_detail(job_id: str, **extra) -> dict:
    """Build event detail with correlation_id and schema_version."""
    return {
        "schema_version": EVENT_SCHEMA_VERSION,
        "correlation_id": job_id,
        **extra,
    }


def publish_pipeline_started(job_id: str, total_stages: int = 0) -> str | None:
    return _get_publisher().publish_pipeline_event(
        "pipeline.started", job_id,
        _base_detail(job_id, started_stages=total_stages),
    )


def publish_stage_completed(job_id: str, stage: str, progress: int, duration_ms: float, artifact_key: str = "") -> str | None:
    return _get_publisher().publish_pipeline_event(
        "pipeline.stage.completed", job_id,
        _base_detail(job_id, stage=stage, progress=progress, duration_ms=duration_ms, artifact_key=artifact_key),
    )


def publish_stage_failed(job_id: str, stage: str, error: str) -> str | None:
    return _get_publisher().publish_pipeline_event(
        "pipeline.stage.failed", job_id,
        _base_detail(job_id, stage=stage, error=error),
    )


def publish_pipeline_completed(job_id: str, total_duration_ms: float, artifact_count: int, is_degraded: bool) -> str | None:
    return _get_publisher().publish_pipeline_event(
        "pipeline.completed", job_id,
        _base_detail(job_id, total_duration_ms=total_duration_ms, artifact_count=artifact_count, is_degraded=is_degraded),
    )


def publish_pipeline_failed(job_id: str, failed_stage: str, error: str) -> str | None:
    return _get_publisher().publish_pipeline_event(
        "pipeline.failed", job_id,
        _base_detail(job_id, failed_stage=failed_stage, error=error),
    )


def publish_report_generated(job_id: str, report_type: str, artifact_key: str) -> str | None:
    return _get_publisher().publish_report_event(
        "report.generated", job_id,
        _base_detail(job_id, report_type=report_type, artifact_key=artifact_key),
    )
