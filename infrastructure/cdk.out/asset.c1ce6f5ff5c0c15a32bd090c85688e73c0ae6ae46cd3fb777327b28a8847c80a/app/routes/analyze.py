import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..models.schemas import JobResponse, JobStatus, AnalysisPhase
from ..utils.aws import get_s3_client, get_s3_bucket

router = APIRouter()


@router.post("/analyze/{job_id}", response_model=JobResponse)
async def start_analysis(job_id: str, background_tasks: BackgroundTasks):
    s3 = get_s3_client()
    bucket = get_s3_bucket()

    try:
        obj = s3.get_object(Bucket=bucket, Key=f"jobs/{job_id}/metadata.json")
        job = json.loads(obj["Body"].read().decode())
    except Exception:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] not in [JobStatus.UPLOADED.value, JobStatus.FAILED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Job is in '{job['status']}' state, cannot start analysis",
        )

    job["status"] = JobStatus.ANALYZING.value
    job["current_phase"] = AnalysisPhase.UPLOAD.value
    job["progress"] = 5
    job["error"] = None
    _update_job(s3, bucket, job_id, job)

    background_tasks.add_task(_run_analysis_pipeline, job_id)

    return JobResponse(**job)


@router.post("/analyze/{job_id}/phase/{phase}")
async def update_phase(job_id: str, phase: AnalysisPhase, progress: int = 0):
    s3 = get_s3_client()
    bucket = get_s3_bucket()

    try:
        obj = s3.get_object(Bucket=bucket, Key=f"jobs/{job_id}/metadata.json")
        job = json.loads(obj["Body"].read().decode())
    except Exception:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job["current_phase"] = phase.value
    job["progress"] = progress
    _update_job(s3, bucket, job_id, job)

    return {"status": "updated", "phase": phase.value, "progress": progress}


def _run_analysis_pipeline(job_id: str):
    try:
        from ..services.orchestrator import run_full_analysis

        run_full_analysis(job_id)
    except Exception as e:
        s3 = get_s3_client()
        bucket = get_s3_bucket()
        try:
            obj = s3.get_object(Bucket=bucket, Key=f"jobs/{job_id}/metadata.json")
            job = json.loads(obj["Body"].read().decode())
        except Exception:
            job = {"job_id": job_id}

        job["status"] = JobStatus.FAILED.value
        job["error"] = str(e)
        _update_job(s3, bucket, job_id, job)


def _update_job(s3, bucket, job_id, job):
    from datetime import datetime, timezone

    job["updated_at"] = datetime.now(timezone.utc).isoformat()
    s3.put_object(
        Bucket=bucket,
        Key=f"jobs/{job_id}/metadata.json",
        Body=json.dumps(job),
        ContentType="application/json",
    )
