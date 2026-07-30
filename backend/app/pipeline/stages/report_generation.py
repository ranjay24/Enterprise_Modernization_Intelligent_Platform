"""Report generation stage — produces all reports using shared builders."""

from __future__ import annotations

import json

import structlog

from app.artifacts.models import Artifact, ArtifactMetadata
from app.artifacts.version import ArtifactVersioner
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage
from app.reports.builders import build_all_reports

logger = structlog.get_logger(__name__)


class ReportGenerationStage(PipelineStage):
    """Generates structured reports from assembled results."""

    name = "report_generation"
    phase = "report_generation"
    generator = "sprint4-pipeline"
    depends_on: list[str] = ["results_assembly"]

    def validate_prerequisites(self, context: PipelineContext) -> list[str]:
        if not context.get_result_data("results_assembly"):
            return ["results_assembly stage must complete first"]
        return []

    def execute(self, context: PipelineContext) -> Artifact:
        results = context.get_result_data("results_assembly")
        reports = build_all_reports(results)

        versioner = ArtifactVersioner()
        content_json = json.dumps(reports, default=str)
        return Artifact(
            metadata=ArtifactMetadata(
                artifact_id=versioner.generate_artifact_id(),
                artifact_type=self.name,
                job_id=context.job_id,
                generator=self.generator,
                platform_version=versioner.get_platform_version(),
                checksum=versioner.compute_checksum(reports),
                size_bytes=len(content_json),
            ),
            content=reports,
        )
