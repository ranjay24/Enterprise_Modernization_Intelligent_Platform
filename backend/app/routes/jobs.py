"""Job management routes — pause, cancel, resume, delete."""

import structlog
from fastapi import APIRouter

from app.aws.dynamodb import JobRepository
from app.aws.s3 import S3Repository
from app.exceptions.custom import ResourceNotFoundException, ValidationFailedException
from app.models.schemas import JobResponse
from app.validators.project_validator import validate_job_id

router = APIRouter()
logger = structlog.get_logger(__name__)

# Jobs that can be paused or cancelled
ACTIVE_STATUSES = {"uploaded", "analyzing"}
PAUSABLE_STATUSES = {"analyzing"}


@router.post("/jobs/{job_id}/pause", response_model=JobResponse)
async def pause_job(job_id: str):
    """Pause a running analysis job. The pipeline will stop before the next stage."""
    validate_job_id(job_id)
    repo = JobRepository()
    job = repo.get_job(job_id)
    if not job:
        raise ResourceNotFoundException("Job", job_id)
    if job.status not in PAUSABLE_STATUSES:
        raise ValidationFailedException(
            f"Job is in '{job.status}' state, can only pause jobs that are 'analyzing'"
        )
    repo.update_job(job_id=job_id, status="paused", current_phase="pausing")
    logger.info("job_paused", job_id=job_id)
    updated = repo.get_job(job_id)
    return JobResponse(**updated.to_dict())


@router.post("/jobs/{job_id}/resume", response_model=JobResponse)
async def resume_job(job_id: str):
    """Resume a paused analysis job from the last checkpoint."""
    validate_job_id(job_id)
    repo = JobRepository()
    job = repo.get_job(job_id)
    if not job:
        raise ResourceNotFoundException("Job", job_id)
    if job.status != "paused":
        raise ValidationFailedException(
            f"Job is in '{job.status}' state, can only resume paused jobs"
        )
    repo.update_job(job_id=job_id, status="uploaded", current_phase="resuming")
    logger.info("job_resumed", job_id=job_id)
    updated = repo.get_job(job_id)
    return JobResponse(**updated.to_dict())


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: str):
    """Cancel a running or queued job permanently."""
    validate_job_id(job_id)
    repo = JobRepository()
    job = repo.get_job(job_id)
    if not job:
        raise ResourceNotFoundException("Job", job_id)
    if job.status in ("analysis_complete", "failed", "cancelled"):
        raise ValidationFailedException(
            f"Job is in '{job.status}' state, cannot cancel"
        )
    repo.update_job(job_id=job_id, status="cancelled", current_phase="cancelled")
    logger.info("job_cancelled", job_id=job_id)
    updated = repo.get_job(job_id)
    return JobResponse(**updated.to_dict())


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and all its associated data (DynamoDB, S3, artifacts)."""
    validate_job_id(job_id)
    repo = JobRepository()
    job = repo.get_job(job_id)
    if not job:
        raise ResourceNotFoundException("Job", job_id)

    # Delete S3 objects (analysis results, artifacts)
    try:
        s3 = S3Repository()
        s3.delete_prefix(f"jobs/{job_id}/")
        logger.info("job_s3_deleted", job_id=job_id)
    except Exception as exc:
        logger.warning("job_s3_delete_failed", job_id=job_id, error=str(exc))

    # Delete DynamoDB record
    try:
        repo.delete_job(job_id)
        logger.info("job_dynamodb_deleted", job_id=job_id)
    except Exception as exc:
        logger.warning("job_dynamodb_delete_failed", job_id=job_id, error=str(exc))

    return {"status": "deleted", "job_id": job_id}


@router.delete("/jobs")
async def delete_all_jobs():
    """Delete ALL jobs and associated data. Fresh start."""
    repo = JobRepository()
    deleted = 0
    try:
        jobs = repo.list_jobs()
        for job in jobs:
            jid = job.job_id
            try:
                s3 = S3Repository()
                s3.delete_prefix(f"jobs/{jid}/")
            except Exception:
                pass
            try:
                repo.delete_job(jid)
                deleted += 1
            except Exception:
                pass
        logger.info("all_jobs_deleted", count=deleted)
    except Exception as exc:
        logger.error("delete_all_failed", error=str(exc))

    return {"status": "deleted", "count": deleted}
