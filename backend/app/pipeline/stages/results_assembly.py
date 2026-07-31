"""Results assembly stage — aggregates all artifacts into a single results.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog

from app.artifacts.models import Artifact, ArtifactMetadata
from app.artifacts.version import ArtifactVersioner
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage

logger = structlog.get_logger(__name__)


class ResultsAssemblyStage(PipelineStage):
    """Assembles all stage outputs into a single results artifact."""

    name = "results_assembly"
    phase = "results_assembly"
    generator = "sprint4-pipeline"
    depends_on: list[str] = ["static_analysis", "enterprise_analysis", "ai_boundaries", "ai_readiness", "ai_adrs", "ai_migration", "ai_cost", "ai_explainability"]

    def validate_prerequisites(self, context: PipelineContext) -> list[str]:
        missing = []
        if not context.get_result_data("static_analysis"):
            missing.append("static_analysis")
        return missing

    def execute(self, context: PipelineContext) -> Artifact:
        metrics = context.get_result_data("static_analysis").get("metrics", {})

        boundaries_data = context.get_result_data("ai_boundaries") or {}
        adrs_data = context.get_result_data("ai_adrs") or {}
        migration_data = context.get_result_data("ai_migration") or {}

        service_boundaries = []
        for svc in boundaries_data.get("services", []):
            service_boundaries.append({
                "name": svc.get("name", "Unknown"),
                "description": svc.get("description", ""),
                "cohesion_score": svc.get("cohesion_score", 50),
                "coupling_score": svc.get("coupling_score", 50),
                "classes": svc.get("classes", []) or [],
                "packages": svc.get("packages", []) or [],
                "api_endpoints": svc.get("api_endpoints", []) or [],
                "database_tables": svc.get("database_tables", []) or [],
                "confidence": svc.get("confidence", 50),
                "readiness": svc.get("readiness", "yellow"),
                "risk_level": svc.get("risk_level", "medium"),
                "business_capability": svc.get("business_capability", ""),
            })

        full_results = {
            "job_id": context.job_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "service_boundaries": service_boundaries,
            "readiness": context.get_result_data("ai_readiness") or {},
            "adrs": adrs_data.get("adrs", []),
            "migration_waves": migration_data.get("waves", []),
            "cost_comparison": context.get_result_data("ai_cost") or {},
            "explainability": context.get_result_data("ai_explainability") or {},
            "sprint2_analysis": context.get_result_data("enterprise_analysis"),
        }

        # Run post-assembly validation and compute quality score
        try:
            from app.validation.analysis_validator import AnalysisValidator
            from app.validation.quality_score import compute_analysis_quality

            validator = AnalysisValidator()
            v_results = validator.validate(full_results)
            quality = compute_analysis_quality(v_results)

            full_results["validation"] = {
                "results": [v.to_dict() for v in v_results],
                "quality": quality,
            }
        except Exception as e:
            logger.warning("results_validation_failed", error=str(e))

        versioner = ArtifactVersioner()
        content_json = json.dumps(full_results, default=str)
        return Artifact(
            metadata=ArtifactMetadata(
                artifact_id=versioner.generate_artifact_id(),
                artifact_type=self.name,
                job_id=context.job_id,
                generator=self.generator,
                platform_version=versioner.get_platform_version(),
                checksum=versioner.compute_checksum(full_results),
                size_bytes=len(content_json),
            ),
            content=full_results,
        )
