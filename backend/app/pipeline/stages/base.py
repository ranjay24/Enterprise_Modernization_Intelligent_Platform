"""Base AI stage — eliminates duplicated try/except pattern across AI stages."""

from __future__ import annotations

import json

import structlog

from app.artifacts.models import Artifact, ArtifactMetadata
from app.artifacts.version import ArtifactVersioner
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage

logger = structlog.get_logger(__name__)


class BaseAIStage(PipelineStage):
    """Base class for all AI-powered pipeline stages.

    Subclasses define:
      - name, phase, requires_ai (inherited from PipelineStage)
      - prerequisites(context) -> list[str]
      - execute_ai(context) -> tuple[dict, str]
        Returns (result_dict, model_id). May raise on failure.
      - fallback() -> dict
        Returns default degraded result when AI fails.

    The base class handles:
      - try/except with fallback
      - Artifact creation with metadata
      - Degraded flagging
    """

    def validate_prerequisites(self, context: PipelineContext) -> list[str]:
        return self.prerequisites(context)

    def prerequisites(self, context: PipelineContext) -> list[str]:
        """Override to declare stage prerequisites."""
        return []

    def execute(self, context: PipelineContext) -> Artifact:
        is_degraded = False
        model_id = ""

        try:
            result, model_id = self.execute_ai(context)
            if not result:
                result = self.fallback()
                is_degraded = True
                model_id = f"{model_id}-empty"
        except Exception as exc:
            logger.warning(
                "ai_stage_fallback",
                stage=self.name,
                job_id=context.job_id,
                error=str(exc),
            )
            result = self.fallback()
            is_degraded = True
            model_id = "deterministic-fallback"

        content_json = json.dumps(result, default=str)
        versioner = ArtifactVersioner()
        return Artifact(
            metadata=ArtifactMetadata(
                artifact_id=versioner.generate_artifact_id(),
                artifact_type=self.name,
                job_id=context.job_id,
                generator=self.generator,
                model_id=model_id,
                platform_version=versioner.get_platform_version(),
                checksum=versioner.compute_checksum(result),
                size_bytes=len(content_json),
                is_degraded=is_degraded,
            ),
            content=result,
        )

    def execute_ai(self, context: PipelineContext) -> tuple[dict, str]:
        """Run the AI function. Returns (result, model_id).

        Override in subclasses. Raise on failure to trigger fallback.
        """
        raise NotImplementedError

    def fallback(self) -> dict:
        """Return a degraded default result. Override in subclasses."""
        return {}
