"""Analysis trigger route — SQS async when deployed, synchronous fallback for local dev."""

import os
import threading

import structlog
from fastapi import APIRouter, Query

from app.aws.dynamodb import JobRepository
from app.aws.sqs import SQSRepository
from app.exceptions.custom import ResourceNotFoundException, ValidationFailedException
from app.models.schemas import AnalysisPhase, JobResponse, JobStatus
from app.services.checkpoint import CheckpointManager
from app.validators.project_validator import validate_job_id

router = APIRouter()
logger = structlog.get_logger(__name__)


def _run_analysis_sync(job_id: str, resume_from: str = None):
    """Run the analysis pipeline directly (local dev fallback)."""
    try:
        from app.services.workers.analysis_worker import handle_analysis_job
        handle_analysis_job(job_id, resume_from=resume_from)
    except Exception as exc:
        logger.error("sync_analysis_failed", job_id=job_id, error=str(exc))


def _is_local() -> bool:
    """Check if running locally (no Lambda worker available)."""
    return os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is None


@router.post("/analyze/{job_id}", response_model=JobResponse)
async def start_analysis(
    job_id: str,
    resume: bool = Query(default=False, description="Resume from last checkpoint"),
):
    validate_job_id(job_id)
    job_repo = JobRepository()
    checkpoint_mgr = CheckpointManager()

    job_domain = job_repo.get_job(job_id)
    if not job_domain:
        raise ResourceNotFoundException("Job", job_id)

    if job_domain.status not in [JobStatus.UPLOADED.value, JobStatus.FAILED.value, JobStatus.PAUSED.value]:
        if not resume:
            raise ValidationFailedException(
                f"Job is in '{job_domain.status}' state, cannot start analysis"
            )

    resume_from = None
    if resume and checkpoint_mgr.has_checkpoint(job_id):
        resume_from = checkpoint_mgr.get_resume_stage(job_id)
        logger.info("analysis_resuming", job_id=job_id, resume_from=resume_from)
    else:
        checkpoint_mgr.clear_checkpoint(job_id)

    # Update job status immediately so frontend sees progress
    job_repo.update_job(
        job_id=job_id,
        status=JobStatus.ANALYZING.value,
        current_phase=AnalysisPhase.UPLOAD.value,
        progress=5,
        error=None,
    )

    if _is_local():
        # Local dev: run pipeline in background thread directly
        logger.info("analysis_local_sync", job_id=job_id)
        thread = threading.Thread(
            target=_run_analysis_sync,
            args=(job_id,),
            kwargs={"resume_from": resume_from},
            daemon=True,
        )
        thread.start()
    else:
        # Production: enqueue to SQS for Worker Lambda
        sqs_repo = SQSRepository()
        message_body = {"job_id": job_id}
        if resume_from:
            message_body["resume_from"] = resume_from

        message_id = sqs_repo.enqueue_analysis(job_id, message_body)
        if not message_id:
            raise ValidationFailedException("Failed to enqueue analysis job")
        logger.info("analysis_enqueued", job_id=job_id, message_id=message_id)

    updated = job_repo.get_job(job_id)
    return JobResponse(**updated.to_dict())


@router.post("/analyze/{job_id}/phase/{phase}")
async def update_phase(job_id: str, phase: AnalysisPhase, progress: int = 0):
    validate_job_id(job_id)
    job_repo = JobRepository()

    job_domain = job_repo.get_job(job_id)
    if not job_domain:
        raise ResourceNotFoundException("Job", job_id)

    job_repo.update_job(
        job_id=job_id,
        current_phase=phase.value,
        progress=progress,
    )

    return {"status": "updated", "phase": phase.value, "progress": progress}
