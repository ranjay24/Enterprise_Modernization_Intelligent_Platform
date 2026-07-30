"""Pipeline engine — orchestrates artifact-first analysis."""

from __future__ import annotations

from collections.abc import Callable

import structlog

from app.artifacts.repository import ArtifactRepository
from app.artifacts.version import ArtifactVersioner
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage
from app.pipeline.state import PipelineState, PipelineStatus

logger = structlog.get_logger(__name__)


class PipelineCancelled(Exception):
    """Raised when a pipeline is cancelled via the pause/cancel flag."""


class PipelineEngine:
    """Orchestrates a sequence of PipelineStages.

    Each stage produces an Artifact stored via ArtifactRepository.
    Supports resume from checkpoints and deterministic fallback.
    When parallel=True, uses DAG-based parallel execution.
    """

    def __init__(
        self,
        stages: list[PipelineStage],
        artifact_repo: ArtifactRepository | None = None,
        parallel: bool = False,
        max_workers: int = 4,
    ):
        self._stages = stages
        self._artifact_repo = artifact_repo or ArtifactRepository()
        self._versioner = ArtifactVersioner()
        self._last_context: PipelineContext | None = None
        self._parallel = parallel
        self._max_workers = max_workers

    @property
    def stages(self) -> list[PipelineStage]:
        return list(self._stages)

    @property
    def stage_names(self) -> list[str]:
        return [s.name for s in self._stages]

    @property
    def last_context(self) -> PipelineContext | None:
        """Access the pipeline context after execution completes."""
        return self._last_context

    def execute(
        self,
        job_id: str,
        initial_data: dict | None = None,
        resume_from: str | None = None,
        progress_callback: Callable[[str, int, str], None] | None = None,
        status_check_fn: Callable[[], str] | None = None,
        parallel: bool | None = None,
    ) -> PipelineState:
        """Execute the full pipeline. Returns final PipelineState.

        Args:
            job_id: The job identifier.
            initial_data: Optional initial context data.
            resume_from: Stage name to resume from.
            progress_callback: Called as callback(job_id, progress_pct, stage_name) after each stage.
            status_check_fn: Called before each stage; returns current job status.
                             If it returns 'paused' or 'cancelled', the pipeline stops.
            parallel: Override the constructor parallel setting.
        """
        use_parallel = parallel if parallel is not None else self._parallel

        if use_parallel:
            from app.scheduling.executor import ParallelExecutor
            executor = ParallelExecutor(
                stages=self._stages,
                artifact_repo=self._artifact_repo,
                max_workers=self._max_workers,
            )
        else:
            from app.scheduling.executor import SequentialExecutor
            executor = SequentialExecutor(
                stages=self._stages,
                artifact_repo=self._artifact_repo,
            )

        state = executor.execute(
            job_id=job_id,
            initial_data=initial_data,
            resume_from=resume_from,
            progress_callback=progress_callback,
            status_check_fn=status_check_fn,
        )

        logger.info(
            "pipeline_completed",
            job_id=job_id,
            total_duration_ms=round(state.total_duration_ms, 2),
            stages_completed=len([s for s in state.stages.values() if s.status == PipelineStatus.COMPLETED]),
            stages_failed=len([s for s in state.stages.values() if s.status == PipelineStatus.FAILED]),
            total_artifacts=state.total_artifacts,
            parallel=use_parallel,
        )

        return state
