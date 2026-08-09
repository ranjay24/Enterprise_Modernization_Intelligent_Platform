"""Manifest stage — generates the final analysis manifest."""

from __future__ import annotations

import json

import structlog

from app.artifacts.models import Artifact, ArtifactManifest, ArtifactMetadata
from app.artifacts.version import ArtifactVersioner
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage
from app.pipeline.state import PipelineStatus

logger = structlog.get_logger(__name__)

SCHEMA_VERSION = "1.0.0"


class ManifestStage(PipelineStage):
    """Generates the final analysis manifest with all artifact metadata."""

    name = "manifest"
    phase = "manifest"
    generator = "sprint4-pipeline"
    depends_on: list[str] = ["results_assembly"]

    def validate_prerequisites(self, context: PipelineContext) -> list[str]:
        if not context.get_result_data("results_assembly"):
            return ["results_assembly stage must complete first"]
        return []

    def execute(self, context: PipelineContext) -> Artifact:
        versioner = ArtifactVersioner()

        # Collect all artifact metadata
        artifact_metadata = []
        degraded_stages = []

        for stage_name, stage_state in context.state.stages.items():
            if stage_state.status in (PipelineStatus.COMPLETED, PipelineStatus.CACHED):
                artifact = context.results.get(stage_name)
                if artifact:
                    artifact_metadata.append(artifact.metadata)
                if stage_state.is_degraded:
                    degraded_stages.append(stage_name)

        usage = {"total_cost": 0.0, "total_input_tokens": 0, "total_output_tokens": 0, "invocations": 0}
        try:
            from app.ai.service import get_ai_engine

            usage = get_ai_engine().provider_registry.cost_tracker.get_job_usage(context.job_id)
        except Exception as exc:
            logger.warning("manifest_cost_tracker_unavailable", job_id=context.job_id, error=str(exc))

        # Get project name from enterprise_analysis results
        sprint2 = context.get_result_data("enterprise_analysis")
        project_name = sprint2.get("project_summary", {}).get("project_name", "Unknown")

        manifest = ArtifactManifest(
            job_id=context.job_id,
            project_name=project_name,
            started_at=context.state.started_at,
            completed_at=context.state.completed_at or versioner.now_iso(),
            total_duration_ms=context.state.total_duration_ms,
            platform_version=versioner.get_platform_version(),
            analysis_version="2.0.0",
            engine_version="1.0.0",
            artifacts=artifact_metadata,
            reports=[],
            pipeline_state=context.state.to_dict(),
            ai_summary={
                "total_tokens_used": usage["total_input_tokens"] + usage["total_output_tokens"],
                "total_cost_estimate": round(usage["total_cost"], 6),
                "deterministic_fallbacks": len(degraded_stages),
                "degraded_stages": degraded_stages,
            },
        )

        manifest_dict = manifest.to_dict()
        manifest_dict["schema_version"] = SCHEMA_VERSION
        manifest.checksum = versioner.compute_checksum(manifest_dict)

        logger.info(
            "manifest_generated",
            job_id=context.job_id,
            artifact_count=len(artifact_metadata),
            total_duration_ms=round(context.state.total_duration_ms, 2),
        )

        return Artifact(
            metadata=ArtifactMetadata(
                artifact_id=versioner.generate_artifact_id(),
                artifact_type=self.name,
                job_id=context.job_id,
                generator=self.generator,
                platform_version=versioner.get_platform_version(),
                checksum=manifest.checksum,
                size_bytes=len(json.dumps(manifest_dict, default=str)),
            ),
            content=manifest_dict,
        )
