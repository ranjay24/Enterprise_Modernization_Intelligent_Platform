import json
from fastapi import APIRouter, HTTPException
from ..models.schemas import JobResponse, AnalysisResult
from ..utils.aws import get_s3_client, get_s3_bucket

router = APIRouter()


@router.get("/results/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    s3 = get_s3_client()
    bucket = get_s3_bucket()

    try:
        obj = s3.get_object(Bucket=bucket, Key=f"jobs/{job_id}/metadata.json")
        job = json.loads(obj["Body"].read().decode())
    except Exception:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobResponse(**job)


@router.get("/results/{job_id}/analysis")
async def get_analysis_results(job_id: str):
    s3 = get_s3_client()
    bucket = get_s3_bucket()

    try:
        obj = s3.get_object(
            Bucket=bucket, Key=f"jobs/{job_id}/analysis/results.json"
        )
        return json.loads(obj["Body"].read().decode())
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis results not found for job {job_id}",
        )


@router.get("/results/{job_id}/artifacts/{filename}")
async def download_artifact(job_id: str, filename: str):
    s3 = get_s3_client()
    bucket = get_s3_bucket()

    try:
        obj = s3.get_object(
            Bucket=bucket, Key=f"jobs/{job_id}/artifacts/{filename}"
        )
        return obj["Body"].read().decode()
    except Exception:
        raise HTTPException(
            status_code=404, detail=f"Artifact '{filename}' not found"
        )


@router.get("/jobs")
async def list_jobs():
    s3 = get_s3_client()
    bucket = get_s3_bucket()
    jobs = []

    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=bucket, Prefix="jobs/", Delimiter="/"
        ):
            for prefix in page.get("CommonPrefixes", []):
                job_id = prefix["Prefix"].split("/")[-2]
                try:
                    obj = s3.get_object(
                        Bucket=bucket, Key=f"jobs/{job_id}/metadata.json"
                    )
                    job = json.loads(obj["Body"].read().decode())
                    jobs.append(job)
                except Exception:
                    continue
    except Exception:
        pass

    return {"jobs": sorted(jobs, key=lambda x: x.get("created_at", ""), reverse=True)}
