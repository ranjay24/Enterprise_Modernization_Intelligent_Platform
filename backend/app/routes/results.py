"""Results, artifacts, and job listing routes — uses DynamoDB + S3 repositories."""

import json

import structlog
from fastapi import APIRouter

from app.artifacts.repository import ArtifactRepository
from app.aws.dynamodb import JobRepository
from app.aws.s3 import S3Repository
from app.capabilities.registry import CapabilityRegistry
from app.exceptions.custom import ResourceNotFoundException
from app.models.schemas import JobResponse
from app.validators.project_validator import validate_job_id

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/results/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    validate_job_id(job_id)
    job_repo = JobRepository()
    job_domain = job_repo.get_job(job_id)
    if not job_domain:
        raise ResourceNotFoundException("Job", job_id)
    return JobResponse(**job_domain.to_dict())


@router.get("/results/{job_id}/analysis")
async def get_analysis_results(job_id: str):
    validate_job_id(job_id)

    # Preferred: load from artifact repository (actual analysis data)
    artifact_repo = ArtifactRepository()
    artifact = artifact_repo.load(job_id, "results_assembly")
    if artifact and "metrics" in artifact.content:
        return artifact.content

    # Fallback: legacy S3 path (may contain pipeline state for older jobs)
    s3_repo = S3Repository()
    try:
        obj = s3_repo.get_object(key=f"jobs/{job_id}/analysis/results.json")
        data = json.loads(obj["Body"].read().decode())
        if "metrics" in data:
            return data
    except Exception:
        pass

    raise ResourceNotFoundException("Analysis results", job_id)


@router.get("/results/{job_id}/artifacts")
async def list_artifacts(job_id: str):
    validate_job_id(job_id)
    job_repo = JobRepository()
    job = job_repo.get_job(job_id)
    if not job:
        raise ResourceNotFoundException("Job", job_id)
    artifact_repo = ArtifactRepository()
    artifacts = artifact_repo.list_artifacts(job_id)
    return {"artifacts": [a.to_dict() for a in artifacts], "count": len(artifacts)}


@router.get("/results/{job_id}/artifacts/{artifact_name}")
async def get_artifact(job_id: str, artifact_name: str):
    validate_job_id(job_id)
    artifact_repo = ArtifactRepository()
    artifact = artifact_repo.load_artifact(job_id, artifact_name)
    if not artifact:
        raise ResourceNotFoundException("Artifact", f"{job_id}/{artifact_name}")
    return artifact.to_dict()


@router.get("/results/{job_id}/artifacts/{artifact_name}/content")
async def get_artifact_content(job_id: str, artifact_name: str):
    validate_job_id(job_id)
    artifact_repo = ArtifactRepository()
    content = artifact_repo.load_content(job_id, artifact_name)
    if content is None:
        raise ResourceNotFoundException("Artifact content", f"{job_id}/{artifact_name}")
    return {"artifact_name": artifact_name, "content": content}


@router.get("/results/{job_id}/manifest")
async def get_manifest(job_id: str):
    validate_job_id(job_id)
    artifact_repo = ArtifactRepository()
    manifest = artifact_repo.load_manifest(job_id)
    if not manifest:
        raise ResourceNotFoundException("Manifest", job_id)
    return manifest


@router.get("/results/{job_id}/artifacts/{filename}")
async def download_artifact_file(job_id: str, filename: str):
    validate_job_id(job_id)
    s3_repo = S3Repository()

    try:
        obj = s3_repo.get_object(key=f"jobs/{job_id}/artifacts/{filename}")
        return obj["Body"].read().decode()
    except Exception:
        raise ResourceNotFoundException("Artifact", filename)


@router.get("/jobs")
async def list_jobs():
    job_repo = JobRepository()
    jobs = job_repo.list_jobs()
    return {"jobs": [j.to_dict() for j in jobs]}


@router.get("/capabilities")
async def list_capabilities():
    registry = CapabilityRegistry()
    return registry.to_dict()


@router.get("/capabilities/{category}")
async def list_capabilities_by_category(category: str):
    from app.capabilities.models import CapabilityCategory
    try:
        cat = CapabilityCategory(category)
    except ValueError:
        return {"error": f"Unknown category: {category}", "valid": [c.value for c in CapabilityCategory]}
    registry = CapabilityRegistry()
    caps = registry.list_by_category(cat)
    return {"category": category, "capabilities": [c.to_dict() for c in caps], "count": len(caps)}
