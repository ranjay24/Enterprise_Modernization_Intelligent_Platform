import os
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models.schemas import JobResponse, JobStatus
from ..utils.aws import get_s3_client, get_s3_bucket

router = APIRouter()


@router.post("/upload", response_model=JobResponse)
async def upload_codebase(file: UploadFile = File(...)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted")

    content = await file.read()
    max_size = 100 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="File exceeds 100MB limit")

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    s3 = get_s3_client()
    bucket = get_s3_bucket()

    try:
        s3.put_object(
            Bucket=bucket,
            Key=f"jobs/{job_id}/raw/{file.filename}",
            Body=content,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {str(e)}")

    job_metadata = {
        "job_id": job_id,
        "status": JobStatus.UPLOADED.value,
        "filename": file.filename,
        "file_size": len(content),
        "created_at": now,
        "updated_at": now,
        "progress": 0,
        "current_phase": None,
        "error": None,
    }

    try:
        s3.put_object(
            Bucket=bucket,
            Key=f"jobs/{job_id}/metadata.json",
            Body=json.dumps(job_metadata),
            ContentType="application/json",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job metadata: {str(e)}",
        )

    return JobResponse(**job_metadata)
