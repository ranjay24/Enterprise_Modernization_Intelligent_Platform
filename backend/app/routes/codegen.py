"""Code generation routes — start/status/architecture/code/review for the agent loop."""

from __future__ import annotations

import os
import threading

import structlog
from fastapi import APIRouter, Query

from app.artifacts.repository import ArtifactRepository
from app.aws.dynamodb import JobRepository
from app.codegen.orchestrator import CodeGenOrchestrator
from app.codegen import models as codegen_models
from app.exceptions.custom import ResourceNotFoundException, ValidationFailedException
from app.validators.project_validator import validate_job_id

router = APIRouter()
logger = structlog.get_logger(__name__)


def _is_local() -> bool:
    return os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is None


def _run_codegen_sync(job_id: str):
    """Run the codegen loop in-process (local dev fallback)."""
    job_repo = JobRepository()
    try:
        orchestrator = CodeGenOrchestrator(progress_callback=_progress_callback)
        orchestrator.run(job_id)
        job_repo.update_job(
            job_id=job_id,
            status="generation_complete",
            current_phase="generation_complete",
            progress=100,
            codegen_stage="finalize",
        )
    except Exception as exc:
        logger.error("codegen_sync_failed", job_id=job_id, error=str(exc))
        try:
            job_repo.update_job(
                job_id=job_id,
                status="failed",
                error=f"Code generation failed: {exc}",
                codegen_stage="failed",
            )
        except Exception:
            pass


def _progress_callback(job_id: str, progress: int, stage: str):
    """Persist codegen progress to DynamoDB so status survives a backend restart."""
    try:
        JobRepository().update_job(job_id=job_id, progress=progress, codegen_stage=stage)
    except Exception:
        pass


@router.post("/codegen/{job_id}/start")
async def start_code_generation(job_id: str):
    validate_job_id(job_id)
    job_repo = JobRepository()
    job = job_repo.get_job(job_id)
    if not job:
        raise ResourceNotFoundException("Job", job_id)
    if job.status not in ("analysis_complete", "generation_complete", "generation_with_warnings", "failed"):
        raise ValidationFailedException(
            f"Job is in '{job.status}' state — analysis must complete before code generation"
        )

    job_repo.update_job(
        job_id=job_id,
        status="generating",
        current_phase="code_generation",
        progress=0,
        codegen_stage="starting",
    )

    if _is_local():
        logger.info("codegen_local_sync", job_id=job_id)
        thread = threading.Thread(
            target=_run_codegen_sync,
            args=(job_id,),
            daemon=True,
        )
        thread.start()
    else:
        raise ValidationFailedException(
            "Code generation runs in local/in-process mode only — the SQS-backed worker is "
            "not deployed yet. Start the backend locally (AWS_LAMBDA_FUNCTION_NAME unset) to trigger codegen."
        )

    return {"status": "started", "job_id": job_id, "current_phase": "code_generation"}


@router.get("/codegen/{job_id}/status")
async def codegen_status(job_id: str):
    validate_job_id(job_id)
    repo = ArtifactRepository()
    job_repo = JobRepository()

    summary = repo.load_content(job_id, "codegen_summary")
    review = repo.load_content(job_id, "review_report")
    plan = repo.load_content(job_id, "codegen_plan")

    # If summary exists, generation is complete - ensure job status reflects it
    if summary and summary.get("status") in ("generation_complete", "generation_with_warnings"):
        job = job_repo.get_job(job_id)
        if job and job.status != summary.get("status"):
            job_repo.update_job(job_id=job_id, status=summary.get("status"), progress=100)

    # Check job database status (progress/stage persist to DynamoDB, so this
    # survives a backend restart — P2.4)
    job = job_repo.get_job(job_id)
    in_progress = job.status == "generating" if job else False
    progress = job.progress if job else (100 if summary else 0)
    current_stage = (
        job.codegen_stage
        if job and job.codegen_stage
        else ("finalize" if summary else "idle")
    )

    service_codes = []
    if plan:
        service_ids = [codegen_models.normalize_service_id(s) for s in codegen_models.normalize_service_list(plan)]
        for sid in service_ids:
            if repo.artifact_exists(job_id, f"service_code_{sid}"):
                service_codes.append(sid)

    return {
        "job_id": job_id,
        "in_progress": in_progress,
        "progress": progress,
        "current_stage": current_stage,
        "summary": summary,
        "review": review,
        "services_generated": service_codes,
        "service_origins": (summary or {}).get("service_origins", {}),
    }


@router.get("/codegen/{job_id}/architecture")
async def codegen_architecture(job_id: str):
    validate_job_id(job_id)
    repo = ArtifactRepository()
    design = repo.load_content(job_id, "architecture_design")
    # Return empty structure if not found (in progress or not generated yet)
    return design or {"version": "1.0.0", "services": [], "nodes": [], "edges": [], "message_topology": {"topics": [], "queues": []}}


@router.get("/codegen/{job_id}/plan")
async def codegen_plan(job_id: str):
    validate_job_id(job_id)
    repo = ArtifactRepository()
    plan = repo.load_content(job_id, "codegen_plan")
    # Return empty structure if not found
    return plan or {"version": "1.0.0", "waves": [], "services": {}, "global_config": {}}


@router.get("/codegen/{job_id}/code")
async def codegen_code(
    job_id: str,
    service: str = Query(default="", description="Filter to a single service"),
):
    validate_job_id(job_id)
    repo = ArtifactRepository()

    plan = repo.load_content(job_id, "codegen_plan")
    service_ids = []
    if plan:
        service_ids = [codegen_models.normalize_service_id(s) for s in codegen_models.normalize_service_list(plan)]

    if service:
        service_ids = [s for s in service_ids if s == service]
        if not service_ids:
            raise ResourceNotFoundException("Service code", service)

    codes = {}
    for sid in service_ids:
        code = repo.load_content(job_id, f"service_code_{sid}")
        if code:
            codes[sid] = codegen_models.normalize_service_code(code)

    return {"job_id": job_id, "services": codes}


@router.get("/codegen/{job_id}/review")
async def codegen_review(job_id: str):
    validate_job_id(job_id)
    repo = ArtifactRepository()
    review = repo.load_content(job_id, "review_report")
    # Return empty report if not found
    return review or {"service_id": "", "iteration": 0, "approved": False, "summary": "Review pending", "score": 0, "findings": []}
