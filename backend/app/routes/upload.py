"""File upload route — thin layer, all storage via repositories."""

import structlog
from fastapi import APIRouter, File, UploadFile

from app.aws.dynamodb import JobRepository
from app.aws.s3 import S3Repository
from app.exceptions.custom import FileUploadException
from app.models.schemas import JobResponse, JobStatus
from app.utils.uuid_provider import generate_uuid
from app.validators.zip_validator import validate_zip_file

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/upload", response_model=JobResponse)
async def upload_codebase(file: UploadFile = File(...)):
    if not file.filename:
        raise FileUploadException("Filename is required")

    content = await file.read()
    validate_zip_file(file.filename, content)

    job_id = generate_uuid()
    s3_repo = S3Repository()
    job_repo = JobRepository()

    try:
        s3_repo.put_object(
            key=f"jobs/{job_id}/raw/{file.filename}",
            body=content,
        )
    except Exception as e:
        logger.error("s3_upload_failed", job_id=job_id, error=str(e))
        raise FileUploadException(f"Failed to store file: {e}")

    job = job_repo.create_job(
        job_id=job_id,
        filename=file.filename,
        file_size=len(content),
        status=JobStatus.UPLOADED.value,
    )

    logger.info("upload_complete", job_id=job_id, filename=file.filename, size=len(content))
    return JobResponse(**job.to_dict())
