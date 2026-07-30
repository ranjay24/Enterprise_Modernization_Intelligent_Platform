"""Pipeline stage — abstract base class for all pipeline stages."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.artifacts.models import Artifact
from app.pipeline.context import PipelineContext


class PipelineStage(ABC):
    """Base class for all pipeline stages.

    Each concrete stage wraps either a Sprint 2 analysis module,
    a Sprint 3 AI function, or a new Sprint 4 capability.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique stage identifier (e.g., 'static_analysis', 'ai_boundaries')."""
        ...

    @property
    @abstractmethod
    def phase(self) -> str:
        """Maps to AnalysisPhase enum value for DynamoDB progress tracking."""
        ...

    @property
    def generator(self) -> str:
        """Identifies which subsystem produced this artifact."""
        return "sprint4-pipeline"

    @property
    def requires_ai(self) -> bool:
        """Whether this stage calls Bedrock."""
        return False

    @property
    def depends_on(self) -> list[str] | None:
        """Explicit dependency stage names.

        If None, the scheduler infers from validate_prerequisites().
        Subclasses should override to declare dependencies explicitly.
        """
        return None

    @abstractmethod
    def execute(self, context: PipelineContext) -> Artifact:
        """Execute the stage and return an artifact."""
        ...

    def validate_prerequisites(self, context: PipelineContext) -> list[str]:
        """Return list of unmet prerequisites. Empty list = all met."""
        return []

    def should_skip(self, context: PipelineContext) -> bool:
        """Return True if this stage should be skipped."""
        return False
