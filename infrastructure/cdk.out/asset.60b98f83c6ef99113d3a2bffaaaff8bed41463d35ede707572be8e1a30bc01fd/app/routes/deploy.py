import json
from fastapi import APIRouter, HTTPException
from ..models.schemas import DeployRequest, DeployResponse
from ..utils.aws import get_s3_client, get_s3_bucket

router = APIRouter()


@router.post("/deploy", response_model=DeployResponse)
async def deploy_service(request: DeployRequest):
    s3 = get_s3_client()
    bucket = get_s3_bucket()

    try:
        obj = s3.get_object(
            Bucket=bucket, Key=f"jobs/{request.job_id}/analysis/results.json"
        )
        analysis = json.loads(obj["Body"].read().decode())
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis results not found for job {request.job_id}",
        )

    service_found = False
    for svc in analysis.get("service_boundaries", []):
        if svc["name"] == request.service_name:
            service_found = True
            break

    if not service_found:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{request.service_name}' not found in analysis",
        )

    import uuid

    deployment_id = str(uuid.uuid4())

    return DeployResponse(
        deployment_id=deployment_id,
        status="deploying",
        service_name=request.service_name,
        ecs_cluster=f"emip-cluster-{request.job_id[:8]}",
        ecs_service=f"emip-svc-{request.service_name.lower()}",
        alb_dns=None,
        health_check_url=None,
    )
