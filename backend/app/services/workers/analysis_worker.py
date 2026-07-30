"""Analysis worker — SQS-triggered Lambda handler for full analysis pipeline."""

from __future__ import annotations

import json

import structlog

from app.artifacts.repository import ArtifactRepository
from app.aws.dynamodb import JobRepository
from app.aws.s3 import S3Repository
from app.pipeline.engine import PipelineEngine
from app.pipeline.stages import (
    AIADRStage,
    AIBoundariesStage,
    AICostStage,
    AIExplainabilityStage,
    AIMigrationStage,
    AIReadinessStage,
    EnterpriseAnalysisStage,
    ExtractionStage,
    ManifestStage,
    ReportGenerationStage,
    ResultsAssemblyStage,
    StaticAnalysisStage,
)
from app.services import events, notifications
from app.services.checkpoint import CheckpointManager

logger = structlog.get_logger(__name__)

# Stage name → human-readable description for progress display
STAGE_DESCRIPTIONS = {
    "extraction": "Extracting source code",
    "static_analysis": "Running static analysis",
    "enterprise_analysis": "Analyzing architecture",
    "ai_boundaries": "Detecting service boundaries",
    "ai_readiness": "Scoring readiness",
    "ai_adrs": "Generating ADRs",
    "ai_migration": "Planning migration waves",
    "ai_cost": "Estimating costs",
    "ai_explainability": "Building explainability",
    "results_assembly": "Assembling results",
    "report_generation": "Generating reports",
    "manifest": "Finalizing",
}


def _build_pipeline() -> PipelineEngine:
    """Build the standard analysis pipeline."""
    stages = [
        ExtractionStage(),
        StaticAnalysisStage(),
        EnterpriseAnalysisStage(),
        AIBoundariesStage(),
        AIReadinessStage(),
        AIADRStage(),
        AIMigrationStage(),
        AICostStage(),
        AIExplainabilityStage(),
        ResultsAssemblyStage(),
        ReportGenerationStage(),
        ManifestStage(),
    ]
    artifact_repo = ArtifactRepository()
    return PipelineEngine(stages=stages, artifact_repo=artifact_repo)


def _update_job(job_id: str, **kwargs):
    """Update job in DynamoDB."""
    try:
        repo = JobRepository()
        repo.update_job(job_id=job_id, **kwargs)
    except Exception as exc:
        logger.warning("job_update_failed", job_id=job_id, error=str(exc))


def _store_analysis(job_id: str, name: str, data: dict):
    """Store analysis result to S3."""
    try:
        s3 = S3Repository()
        s3.put_object(
            key=f"jobs/{job_id}/analysis/{name}.json",
            body=json.dumps(data, default=str),
        )
    except Exception as exc:
        logger.warning("analysis_store_failed", job_id=job_id, name=name, error=str(exc))


def _progress_callback(job_id: str, progress_pct: int, stage_name: str):
    """Called by pipeline engine before and after each stage.

    Before execution: current_phase updated, completed_phases excludes this stage.
    After execution:  progress increased, completed_phases includes this stage.
    """
    stage_list = list(STAGE_DESCRIPTIONS.keys())
    total = len(stage_list)
    if stage_name in stage_list:
        idx = stage_list.index(stage_name)
        # Post-callback has progress_pct >= expected for this stage;
        # pre-callback has progress matching previous stage's post progress.
        expected_post = int((idx + 1) / total * 95)
        if progress_pct >= expected_post:
            completed = stage_list[:idx + 1]
        else:
            completed = stage_list[:idx]
    else:
        completed = []
    _update_job(
        job_id,
        progress=progress_pct,
        current_phase=stage_name,
        completed_phases=completed,
    )
    logger.info("pipeline_progress", job_id=job_id, progress=progress_pct, stage=stage_name)


def _status_check(job_id: str):
    """Called by pipeline engine before each stage to check pause/cancel."""
    try:
        repo = JobRepository()
        job = repo.get_job(job_id)
        if job:
            return job.status
    except Exception:
        pass
    return "analyzing"


def handle_analysis_job(job_id: str, resume_from: str = None) -> dict:
    """Execute the full analysis pipeline for a job.

    This is the main entry point called by the SQS worker.
    """
    checkpoint_mgr = CheckpointManager()
    pipeline = _build_pipeline()

    try:
        # Determine starting state
        initial_data = {}
        if resume_from:
            existing_state = checkpoint_mgr.load(job_id)
            if existing_state:
                initial_data = {"resume_state": existing_state.to_dict()}
                logger.info("resuming_analysis", job_id=job_id, resume_from=resume_from)

        # Update job status
        _update_job(job_id, status="analyzing", current_phase="starting", progress=5)
        events.publish_pipeline_started(job_id, total_stages=len(pipeline.stage_names))

        # Execute pipeline with progress callbacks and status checks
        state = pipeline.execute(
            job_id,
            initial_data=initial_data,
            resume_from=resume_from,
            progress_callback=_progress_callback,
            status_check_fn=lambda: _status_check(job_id),
        )

        # Check if pipeline was paused/cancelled
        current_job = JobRepository().get_job(job_id)
        if current_job and current_job.status in ("paused", "cancelled"):
            _update_job(job_id, current_phase=f"paused_at_{state.status.value}" if hasattr(state.status, 'value') else "paused")
            logger.info("pipeline_paused", job_id=job_id, status=current_job.status)
            return state.to_dict()

        # Store assembled results to S3 for backward compatibility with frontend
        artifact_repo = ArtifactRepository()
        artifact = artifact_repo.load(job_id, "results_assembly")
        assembled = artifact.content if artifact else None
        if assembled:
            _store_analysis(job_id, "results", assembled)
        else:
            _store_analysis(job_id, "results", state.to_dict())

        # Save checkpoint
        checkpoint_mgr.save(job_id, state)

        # Finalize job
        if state.status == "completed":
            _update_job(
                job_id,
                status="analysis_complete",
                current_phase="analysis_complete",
                progress=100,
            )
            events.publish_pipeline_completed(
                job_id,
                total_duration_ms=state.total_duration_ms,
                artifact_count=state.total_artifacts,
                is_degraded=state.is_degraded,
            )
            try:
                notifications.notify_analysis_completed(
                    job_id,
                    duration_ms=state.total_duration_ms,
                )
            except Exception:
                pass
        else:
            failed_stages = [s.stage_name for s in state.stages.values() if s.status.value == "failed"]
            error_msg = f"Pipeline failed at stages: {failed_stages}" if failed_stages else "Pipeline completed with errors"
            _update_job(
                job_id,
                status="analysis_complete",
                current_phase="completed_with_errors",
                progress=100,
                error=error_msg if state.errors else None,
            )
            events.publish_pipeline_completed(
                job_id,
                total_duration_ms=state.total_duration_ms,
                artifact_count=state.total_artifacts,
                is_degraded=state.is_degraded,
            )

        logger.info(
            "analysis_worker_complete",
            job_id=job_id,
            status=state.status,
            duration_ms=round(state.total_duration_ms, 2),
            artifacts=state.total_artifacts,
        )

        return state.to_dict()

    except Exception as exc:
        logger.error("analysis_worker_failed", job_id=job_id, error=str(exc))
        _update_job(job_id, status="failed", error=str(exc))
        events.publish_pipeline_failed(job_id, "worker", str(exc))
        try:
            notifications.notify_analysis_failed(job_id, str(exc))
        except Exception:
            pass
        raise
