"""Static analysis stage — wraps Sprint 2 static analysis."""

from __future__ import annotations

import json

import structlog

from app.artifacts.models import Artifact, ArtifactMetadata
from app.artifacts.version import ArtifactVersioner
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage
from app.services.static_analyzer import analyze_java_codebase

logger = structlog.get_logger(__name__)


class StaticAnalysisStage(PipelineStage):
    """Runs Sprint 2 static analysis on the extracted codebase."""

    name = "static_analysis"
    phase = "static_analysis"
    generator = "sprint2-analysis-engine"
    depends_on: list[str] = ["extraction"]

    def validate_prerequisites(self, context: PipelineContext) -> list[str]:
        extraction = context.get_result_data("extraction")
        if not extraction or not extraction.get("extracted_path"):
            return ["extraction stage must complete first"]
        return []

    def execute(self, context: PipelineContext) -> Artifact:
        extracted_path = context.get_result_data("extraction")["extracted_path"]
        result = analyze_java_codebase(extracted_path)

        # Convert dataclass results to dicts
        analysis_data = {
            "classes": [
                {
                    "name": c.name, "package": c.package, "file_path": c.file_path,
                    "lines_of_code": c.lines_of_code, "method_count": c.method_count,
                    "annotations": c.annotations, "imports": c.imports,
                    "dependencies": c.dependencies, "extends": c.extends,
                    "implements": c.implements, "injected_fields": c.injected_fields,
                    "fields": c.fields, "is_entity": c.is_entity,
                    "is_controller": c.is_controller, "is_service": c.is_service,
                    "is_repository": c.is_repository,
                }
                for c in result.classes
            ],
            "endpoints": [
                {"method": e.method, "path": e.path, "handler_class": e.handler_class,
                 "handler_method": e.handler_method, "annotations": e.annotations}
                for e in result.endpoints
            ],
            "dependency_edges": result.dependency_edges,
            "metrics": result.metrics,
            "package_tree": result.package_tree,
        }

        versioner = ArtifactVersioner()
        return Artifact(
            metadata=ArtifactMetadata(
                artifact_id=versioner.generate_artifact_id(),
                artifact_type=self.name,
                job_id=context.job_id,
                generator=self.generator,
                platform_version=versioner.get_platform_version(),
                checksum=versioner.compute_checksum(analysis_data),
                size_bytes=len(json.dumps(analysis_data, default=str)),
            ),
            content=analysis_data,
        )
