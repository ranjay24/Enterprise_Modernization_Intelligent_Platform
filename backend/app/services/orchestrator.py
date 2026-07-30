"""Analysis pipeline orchestrator — coordinates all analysis phases."""

import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone

import structlog

from app.aws.dynamodb import JobRepository
from app.aws.s3 import S3Repository
from app.core.settings import get_settings
from app.services import bedrock_analyzer
from app.services.analysis_engine import run_analysis as run_sprint2_analysis
from app.services.static_analyzer import analyze_java_codebase

# Sprint 3: AI layer — imports the new orchestrator with same function signatures
try:
    from app.ai import orchestrator as ai_orchestrator
    _AI_LAYER_AVAILABLE = True
except ImportError:
    _AI_LAYER_AVAILABLE = False

logger = structlog.get_logger(__name__)

settings = get_settings()


def run_full_analysis(job_id: str) -> dict:
    s3_repo = S3Repository()
    job_repo = JobRepository()

    try:
        _update_job_phase(job_repo, job_id, "extracting", 10)
        extracted_path = _extract_codebase(s3_repo, job_id)

        _update_job_phase(job_repo, job_id, "static_analysis", 20)
        static_result = analyze_java_codebase(extracted_path)

        analysis_data = {
            "classes": [
                {
                    "name": c.name,
                    "package": c.package,
                    "file_path": c.file_path,
                    "lines_of_code": c.lines_of_code,
                    "method_count": c.method_count,
                    "annotations": c.annotations,
                    "imports": c.imports,
                    "dependencies": c.dependencies,
                    "extends": c.extends,
                    "implements": c.implements,
                    "injected_fields": c.injected_fields,
                    "fields": c.fields,
                    "is_entity": c.is_entity,
                    "is_controller": c.is_controller,
                    "is_service": c.is_service,
                    "is_repository": c.is_repository,
                }
                for c in static_result.classes
            ],
            "endpoints": [
                {
                    "method": e.method,
                    "path": e.path,
                    "handler_class": e.handler_class,
                    "handler_method": e.handler_method,
                    "annotations": e.annotations,
                }
                for e in static_result.endpoints
            ],
            "dependency_edges": static_result.dependency_edges,
            "metrics": static_result.metrics,
            "package_tree": static_result.package_tree,
        }

        _store_analysis(s3_repo, job_id, "static_analysis", analysis_data)

        sprint2_result = {}
        _update_job_phase(job_repo, job_id, "enterprise_analysis", 30)
        try:
            sprint2_result = run_sprint2_analysis(job_id, extracted_path)
            _store_analysis(s3_repo, job_id, "sprint2_analysis", sprint2_result)
            logger.info("sprint2_analysis_complete", job_id=job_id)
        except Exception as e:
            logger.error("sprint2_analysis_failed", error=str(e))
            sprint2_result = {"error": str(e)}
            _store_analysis(s3_repo, job_id, "sprint2_analysis", sprint2_result)

        services = []
        readiness_result = {}
        adr_result = {}
        waves_result = {}
        cost_result = {}
        explainability_result = {}

        _update_job_phase(job_repo, job_id, "service_boundary", 35)
        try:
            if _AI_LAYER_AVAILABLE:
                boundaries_result = ai_orchestrator.analyze_service_boundaries(analysis_data)
                logger.info("ai_layer_used", phase="service_boundary", job_id=job_id)
            else:
                boundaries_result = bedrock_analyzer.analyze_service_boundaries(analysis_data)
            services = boundaries_result.get("services", [])
            _store_analysis(s3_repo, job_id, "boundaries", boundaries_result)
        except Exception as e:
            logger.error("service_boundary_analysis_failed", error=str(e))
            _store_analysis(s3_repo, job_id, "boundaries", {"error": str(e), "services": []})

        _update_job_phase(job_repo, job_id, "readiness_scoring", 50)
        try:
            if _AI_LAYER_AVAILABLE:
                readiness_result = ai_orchestrator.generate_readiness_scores(analysis_data)
            else:
                readiness_result = bedrock_analyzer.generate_readiness_scores(analysis_data)
            _store_analysis(s3_repo, job_id, "readiness", readiness_result)
        except Exception as e:
            logger.error("readiness_scoring_failed", error=str(e))
            readiness_result = {
                "code_quality": 0, "architecture": 0, "cloud_readiness": 0,
                "service_separation": 0, "database_coupling": 0, "documentation": 0,
                "overall": 0, "confidence": 0, "summary": f"Scoring failed: {e}",
            }
            _store_analysis(s3_repo, job_id, "readiness", readiness_result)

        _update_job_phase(job_repo, job_id, "adr_generation", 60)
        try:
            if _AI_LAYER_AVAILABLE:
                adr_result = ai_orchestrator.generate_adrs(analysis_data, services)
            else:
                adr_result = bedrock_analyzer.generate_adrs(analysis_data, services)
            _store_analysis(s3_repo, job_id, "adrs", adr_result)
        except Exception as e:
            logger.error("adr_generation_failed", error=str(e))
            adr_result = {"adrs": []}
            _store_analysis(s3_repo, job_id, "adrs", adr_result)

        _update_job_phase(job_repo, job_id, "migration_planning", 70)
        try:
            if _AI_LAYER_AVAILABLE:
                waves_result = ai_orchestrator.generate_migration_waves(services, readiness_result)
            else:
                waves_result = bedrock_analyzer.generate_migration_waves(services, readiness_result)
            _store_analysis(s3_repo, job_id, "waves", waves_result)
        except Exception as e:
            logger.error("migration_planning_failed", error=str(e))
            waves_result = {"waves": []}
            _store_analysis(s3_repo, job_id, "waves", waves_result)

        _update_job_phase(job_repo, job_id, "cost_analysis", 75)
        try:
            if _AI_LAYER_AVAILABLE:
                cost_result = ai_orchestrator.generate_cost_comparison(analysis_data, services)
            else:
                cost_result = bedrock_analyzer.generate_cost_comparison(analysis_data, services)
            _store_analysis(s3_repo, job_id, "cost", cost_result)
        except Exception as e:
            logger.error("cost_analysis_failed", error=str(e))
            cost_result = {
                "current_monthly": 0, "post_migration_monthly": 0,
                "monthly_savings": 0, "annual_savings": 0,
                "one_time_cost": 0, "payback_months": 0,
                "breakdown_current": {}, "breakdown_post": {},
            }
            _store_analysis(s3_repo, job_id, "cost", cost_result)

        _update_job_phase(job_repo, job_id, "explainability", 80)
        try:
            if _AI_LAYER_AVAILABLE:
                explainability_result = ai_orchestrator.generate_explainability(
                    services, readiness_result, analysis_data
                )
            else:
                explainability_result = bedrock_analyzer.generate_explainability(
                    services, readiness_result, analysis_data
                )
            _store_analysis(s3_repo, job_id, "explainability", explainability_result)
        except Exception as e:
            logger.error("explainability_generation_failed", error=str(e))
            explainability_result = {"recommendations": [], "business_capabilities": [], "risk_heatmap": []}
            _store_analysis(s3_repo, job_id, "explainability", explainability_result)

        _update_job_phase(job_repo, job_id, "code_generation", 95)
        _store_analysis(s3_repo, job_id, "generated_code", {})

        full_results = {
            "job_id": job_id,
            "metrics": static_result.metrics,
            "service_boundaries": services,
            "readiness": readiness_result,
            "adrs": adr_result.get("adrs", []),
            "migration_waves": waves_result.get("waves", []),
            "cost_comparison": cost_result,
            "explainability": explainability_result,
            "sprint2_analysis": sprint2_result,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        _store_analysis(s3_repo, job_id, "results", full_results)

        job_repo.update_job(
            job_id=job_id,
            status="analysis_complete",
            current_phase="analysis_complete",
            progress=100,
        )

        logger.info("analysis_pipeline_complete", job_id=job_id)
        return full_results

    except Exception as e:
        logger.error("pipeline_failed", job_id=job_id, error=str(e))
        job_repo.update_job(job_id=job_id, status="failed", error=str(e))
        raise


def _extract_codebase(s3_repo: S3Repository, job_id: str) -> str:
    paginator = s3_repo.client.get_paginator("list_objects_v2")
    zip_key = None
    for page in paginator.paginate(Bucket=s3_repo.bucket, Prefix=f"jobs/{job_id}/raw/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".zip"):
                zip_key = obj["Key"]
                break
        if zip_key:
            break

    if not zip_key:
        raise ValueError("No ZIP file found in job raw directory")

    tmp_zip = tempfile.mktemp(suffix=".zip")
    s3_repo.client.download_file(s3_repo.bucket, zip_key, tmp_zip)

    extract_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(tmp_zip, "r") as zf:
        zf.extractall(extract_dir)

    os.remove(tmp_zip)
    logger.info("codebase_extracted", path=extract_dir)
    return extract_dir


def _store_analysis(s3_repo: S3Repository, job_id: str, name: str, data: dict):
    s3_repo.put_object(
        key=f"jobs/{job_id}/analysis/{name}.json",
        body=json.dumps(data, default=str),
    )


def _update_job_phase(job_repo: JobRepository, job_id: str, phase: str, progress: int):
    try:
        job_repo.update_job(
            job_id=job_id,
            status="analyzing",
            current_phase=phase,
            progress=progress,
        )
    except Exception as e:
        logger.warning("failed_to_update_job_phase", job_id=job_id, phase=phase, error=str(e))
