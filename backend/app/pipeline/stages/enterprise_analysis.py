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
