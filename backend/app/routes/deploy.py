"""Deployment route — code generation via Bedrock."""

import json

import structlog
from fastapi import APIRouter

from app.aws.dynamodb import JobRepository
from app.aws.s3 import S3Repository
from app.exceptions.custom import AWSServiceException, ResourceNotFoundException
from app.models.schemas import DeployRequest, DeployResponse
from app.services import bedrock_analyzer
from app.utils.uuid_provider import generate_uuid
from app.validators.project_validator import validate_job_id

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/deploy", response_model=DeployResponse)
async def deploy_service(request: DeployRequest):
    validate_job_id(request.job_id)
    s3_repo = S3Repository()
    job_repo = JobRepository()

    try:
        obj = s3_repo.get_object(key=f"jobs/{request.job_id}/analysis/results.json")
        analysis = json.loads(obj["Body"].read().decode())
    except Exception:
        raise ResourceNotFoundException("Analysis results", request.job_id)

    service_boundary = None
    for svc in analysis.get("service_boundaries", []):
        if svc["name"] == request.service_name:
            service_boundary = svc
            break

    if not service_boundary:
        raise ResourceNotFoundException("Service", request.service_name)

    generated_code = analysis.get("generated_code", {})
    code_for_service = generated_code.get(request.service_name)

    if not code_for_service or "error" in code_for_service:
        try:
            static_obj = s3_repo.get_object(key=f"jobs/{request.job_id}/analysis/static_analysis.json")
            analysis_data = json.loads(static_obj["Body"].read().decode())
            code_for_service = bedrock_analyzer.generate_service_code(
                request.service_name, service_boundary, analysis_data
            )
        except Exception as e:
            logger.error("code_generation_failed", job_id=request.job_id, service=request.service_name, error=str(e))
            raise AWSServiceException("Bedrock", f"Code generation failed: {e}")

    deployment_id = generate_uuid()
    s3_repo.put_object(
        key=f"jobs/{request.job_id}/deployments/{deployment_id}/code.json",
        body=json.dumps(code_for_service, default=str),
    )

    logger.info("deployment_complete", job_id=request.job_id, service=request.service_name)
    return DeployResponse(
        deployment_id=deployment_id,
        status="code_generated",
        service_name=request.service_name,
        ecs_cluster=None,
        ecs_service=None,
        alb_dns=None,
        health_check_url=None,
    )
