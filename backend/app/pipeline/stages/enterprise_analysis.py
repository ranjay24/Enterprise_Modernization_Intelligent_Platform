"""Enterprise analysis stage — wraps Sprint 2 plugin engine."""

from __future__ import annotations

import json

import structlog

from app.artifacts.models import Artifact, ArtifactMetadata
from app.artifacts.version import ArtifactVersioner
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage
from app.services.analysis_engine import run_analysis

logger = structlog.get_logger(__name__)


class EnterpriseAnalysisStage(PipelineStage):
    """Runs the Sprint 2 plugin-based analysis engine."""

    name = "enterprise_analysis"
    phase = "enterprise_analysis"
    generator = "sprint2-analysis-engine"
    depends_on: list[str] = ["extraction"]

    def validate_prerequisites(self, context: PipelineContext) -> list[str]:
        extraction = context.get_result_data("extraction")
        if not extraction or not extraction.get("extracted_path"):
            return ["extraction stage must complete first"]
        return []

    def execute(self, context: PipelineContext) -> Artifact:
        extracted_path = context.get_result_data("extraction")["extracted_path"]
        result = run_analysis(context.job_id, extracted_path)

        # Spec 01: attach detected business capabilities to the enterprise
        # artifact so downstream AI stages and the frontend can consume them.
        static_analysis = context.get_result_data("static_analysis")
        if static_analysis:
            from app.ai.context.domains import detect_business_domains
            domains = detect_business_domains(static_analysis)
            result["business_capabilities"] = [
                {
                    "name": d["name"],
                    "entity": d["entity"],
                    "description": d["description"],
                    "confidence": d["confidence"],
                    "classes": d["classes"],
                    "controllers": d["controllers"],
                    "services": d["services"],
                    "repositories": d["repositories"],
                    "api_endpoint_count": len(d["api_endpoints"]),
                    "dependencies": d.get("dependencies", []),
                }
                for d in domains
            ]

        versioner = ArtifactVersioner()
        return Artifact(
            metadata=ArtifactMetadata(
                artifact_id=versioner.generate_artifact_id(),
                artifact_type=self.name,
                job_id=context.job_id,
                generator=self.generator,
                platform_version=versioner.get_platform_version(),
                checksum=versioner.compute_checksum(result),
                size_bytes=len(json.dumps(result, default=str)),
            ),
            content=result,
        )
