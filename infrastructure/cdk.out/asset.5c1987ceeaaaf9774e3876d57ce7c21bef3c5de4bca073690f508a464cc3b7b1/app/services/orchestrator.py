import json
import os
import zipfile
import tempfile
from datetime import datetime, timezone
from ..utils.aws import get_s3_client, get_s3_bucket
from .static_analyzer import analyze_java_codebase
from . import bedrock_analyzer


def run_full_analysis(job_id: str) -> dict:
    s3 = get_s3_client()
    bucket = get_s3_bucket()

    _update_job(s3, bucket, job_id, "extracting", 10)
    extracted_path = _extract_codebase(s3, bucket, job_id)

    _update_job(s3, bucket, job_id, "static_analysis", 20)
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

    _store_analysis(s3, bucket, job_id, "static_analysis", analysis_data)
    _update_job(s3, bucket, job_id, "service_boundary", 35)
    boundaries_result = bedrock_analyzer.analyze_service_boundaries(analysis_data)
    services = boundaries_result.get("services", [])
    _store_analysis(s3, bucket, job_id, "boundaries", boundaries_result)

    _update_job(s3, bucket, job_id, "readiness_scoring", 50)
    readiness_result = bedrock_analyzer.generate_readiness_scores(analysis_data)
    _store_analysis(s3, bucket, job_id, "readiness", readiness_result)

    _update_job(s3, bucket, job_id, "adr_generation", 60)
    adr_result = bedrock_analyzer.generate_adrs(analysis_data, services)
    _store_analysis(s3, bucket, job_id, "adrs", adr_result)

    _update_job(s3, bucket, job_id, "migration_planning", 70)
    waves_result = bedrock_analyzer.generate_migration_waves(services, readiness_result)
    _store_analysis(s3, bucket, job_id, "waves", waves_result)

    _update_job(s3, bucket, job_id, "cost_analysis", 75)
    cost_result = bedrock_analyzer.generate_cost_comparison(analysis_data, services)
    _store_analysis(s3, bucket, job_id, "cost", cost_result)

    _update_job(s3, bucket, job_id, "explainability", 80)
    explainability_result = bedrock_analyzer.generate_explainability(
        services, readiness_result, analysis_data
    )
    _store_analysis(s3, bucket, job_id, "explainability", explainability_result)

    full_results = {
        "job_id": job_id,
        "metrics": static_result.metrics,
        "service_boundaries": services,
        "readiness": readiness_result,
        "adrs": adr_result.get("adrs", []),
        "migration_waves": waves_result.get("waves", []),
        "cost_comparison": cost_result,
        "explainability": explainability_result,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _store_analysis(s3, bucket, job_id, "results", full_results)
    _update_job(s3, bucket, job_id, "analysis_complete", 100)

    return full_results


def _extract_codebase(s3, bucket, job_id) -> str:
    paginator = s3.get_paginator("list_objects_v2")
    zip_key = None
    for page in paginator.paginate(Bucket=bucket, Prefix=f"jobs/{job_id}/raw/"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".zip"):
                zip_key = obj["Key"]
                break
        if zip_key:
            break

    if not zip_key:
        raise ValueError("No ZIP file found in job raw directory")

    tmp_zip = tempfile.mktemp(suffix=".zip")
    s3.download_file(bucket, zip_key, tmp_zip)

    extract_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(tmp_zip, "r") as zf:
        zf.extractall(extract_dir)

    os.remove(tmp_zip)
    return extract_dir


def _store_analysis(s3, bucket, job_id, name, data):
    s3.put_object(
        Bucket=bucket,
        Key=f"jobs/{job_id}/analysis/{name}.json",
        Body=json.dumps(data, default=str),
        ContentType="application/json",
    )


def _update_job(s3, bucket, job_id, phase, progress):
    try:
        obj = s3.get_object(Bucket=bucket, Key=f"jobs/{job_id}/metadata.json")
        job = json.loads(obj["Body"].read().decode())
    except Exception:
        job = {"job_id": job_id}

    job["status"] = "analyzing"
    job["current_phase"] = phase
    job["progress"] = progress
    job["updated_at"] = datetime.now(timezone.utc).isoformat()

    if phase == "analysis_complete":
        job["status"] = "analysis_complete"
        job["progress"] = 100

    s3.put_object(
        Bucket=bucket,
        Key=f"jobs/{job_id}/metadata.json",
        Body=json.dumps(job, default=str),
        ContentType="application/json",
    )
