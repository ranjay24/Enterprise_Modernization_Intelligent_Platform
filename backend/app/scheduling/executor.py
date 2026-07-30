"""Parallel executor — dependency-aware concurrent stage execution."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import Future

import structlog

from app.artifacts.repository import ArtifactRepository
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage
from app.pipeline.state import PipelineState, PipelineStatus
from app.scheduling.dag import DAGBuilder
from app.scheduling.pool import StageTiming, WorkerPool
from app.scheduling.resolver import DependencyResolver

logger = structlog.get_logger(__name__)


class SequentialExecutor:
    """Sequential executor — preserves exact Sprint 4 behavior.

    This is the fallback strategy. It executes stages in list order,
    one at a time, with identical logic to the original PipelineEngine.
    """

    def __init__(self, stages: list[PipelineStage], artifact_repo: ArtifactRepository | None = None):
        self._stages = list(stages)
        self._artifact_repo = artifact_repo or ArtifactRepository()

    def execute(
        self,
        job_id: str,
        initial_data: dict | None = None,
        resume_from: str | None = None,
        progress_callback: Callable | None = None,
        status_check_fn: Callable | None = None,
    ) -> PipelineState:
        context = PipelineContext(
            job_id=job_id,
            data=initial_data or {},
            state=PipelineState(job_id=job_id, status="running"),
        )

        start_time = time.monotonic()
        total_stages = len(self._stages)

        for stage_idx, stage in enumerate(self._stages):
            if status_check_fn:
                try:
                    current_status = status_check_fn()
                    if current_status in ("cancelled", "paused"):
                        logger.info("pipeline_interrupted", job_id=job_id, status=current_status, stage=stage.name)
                        context.state.errors.append({
                            "stage": stage.name,
                            "error": f"Pipeline {current_status} by user",
                            "duration_ms": 0,
                        })
                        break
                except Exception:
                    pass

            if resume_from and stage.name != resume_from and self._is_before(stage.name, resume_from):
                if not context.state.has_completed(stage.name):
                    context.state.mark_started(stage.name)
                    context.state.mark_completed(stage.name)
                self._restore_artifact(job_id, stage.name, context)
                continue

            if context.state.has_completed(stage.name):
                artifact = self._artifact_repo.load(job_id, stage.name)
                if artifact:
                    context.set_result(stage.name, artifact)
                    context.state.mark_cached(stage.name, artifact.metadata.artifact_id)
                continue

            unmet = stage.validate_prerequisites(context)
            if unmet:
                context.state.mark_started(stage.name)
                context.state.mark_failed(stage.name, f"Unmet prerequisites: {unmet}")
                continue

            if stage.should_skip(context):
                context.state.mark_started(stage.name)
                context.state.mark_skipped(stage.name)
                continue

            context.state.mark_started(stage.name)

            # Set current_phase BEFORE execution so frontend shows spinner during the stage
            before_count = stage_idx
            before_pct = min(95, int((before_count / total_stages) * 95))
            if progress_callback:
                try:
                    progress_callback(job_id, before_pct, stage.name)
                except Exception:
                    pass

            stage_start = time.monotonic()
            try:
                artifact = stage.execute(context)
                elapsed = (time.monotonic() - stage_start) * 1000
                artifact.metadata.phase_duration_ms = elapsed
                artifact_key = self._artifact_repo.save(job_id, stage.name, artifact)
                context.set_result(stage.name, artifact)
                context.state.mark_completed(stage.name, artifact_key, artifact.metadata.artifact_id)
                completed_count = stage_idx + 1
                progress_pct = min(95, int((completed_count / total_stages) * 95))
                if progress_callback:
                    try:
                        progress_callback(job_id, progress_pct, stage.name)
                    except Exception:
                        pass
            except Exception as exc:
                elapsed = (time.monotonic() - stage_start) * 1000
                context.state.mark_failed(stage.name, str(exc))

        context.state.total_duration_ms = (time.monotonic() - start_time) * 1000
        context.state.finalize()
        return context.state

    def _restore_artifact(self, job_id: str, stage_name: str, context: PipelineContext) -> None:
        if context.get_result(stage_name) is not None:
            return
        artifact = self._artifact_repo.load(job_id, stage_name)
        if artifact:
            context.set_result(stage_name, artifact)

    def _is_before(self, stage_a: str, stage_b: str) -> bool:
        names = [s.name for s in self._stages]
        try:
            return names.index(stage_a) < names.index(stage_b)
        except ValueError:
            return False


class ParallelExecutor:
    """Parallel executor — dependency-aware concurrent stage execution.

    Executes stages layer by layer. Within each layer, independent stages
    run concurrently via ThreadPoolExecutor. All stages in layer N must
    complete before layer N+1 starts.
    """

    def __init__(
        self,
        stages: list[PipelineStage],
        artifact_repo: ArtifactRepository | None = None,
        max_workers: int = 4,
    ):
        self._stages = list(stages)
        self._artifact_repo = artifact_repo or ArtifactRepository()
        self._max_workers = max_workers

    def execute(
        self,
        job_id: str,
        initial_data: dict | None = None,
        resume_from: str | None = None,
        progress_callback: Callable | None = None,
        status_check_fn: Callable | None = None,
    ) -> PipelineState:
        wall_start = time.monotonic()

        dag = DAGBuilder(self._stages).build()
        errors = dag.validate()
        if errors:
            logger.error("dag_validation_failed", job_id=job_id, errors=errors)
            raise ValueError(f"Invalid dependency graph: {'; '.join(errors)}")

        layers = dag.get_layers()
        resolver = DependencyResolver(dag.adjacency)
        stage_map = {s.name: s for s in self._stages}

        context = PipelineContext(
            job_id=job_id,
            data=initial_data or {},
            state=PipelineState(
                job_id=job_id,
                status="running",
                parallel_execution=True,
                execution_layers=[list(layer) for layer in layers],
                max_concurrency=self._max_workers,
            ),
        )

        pool = WorkerPool(max_workers=self._max_workers)
        total_stages = len(self._stages)
        completed_count = 0
        cancelled = False

        if resume_from:
            self._setup_resume(job_id, resume_from, context, stage_map)

        scheduling_start = time.monotonic()

        for layer_idx, layer in enumerate(layers):
            stages_to_run: list[str] = []
            for stage_name in layer:
                if context.state.has_completed(stage_name):
                    artifact = self._artifact_repo.load(job_id, stage_name)
                    if artifact:
                        context.set_result(stage_name, artifact)
                        context.state.mark_cached(stage_name, artifact.metadata.artifact_id)
                        completed_count += 1
                        if progress_callback:
                            try:
                                pct = min(95, int((completed_count / total_stages) * 95))
                                progress_callback(job_id, pct, stage_name)
                            except Exception:
                                pass
                    continue
                stages_to_run.append(stage_name)

            if not stages_to_run:
                continue

            for stage_name in stages_to_run:
                stage = stage_map[stage_name]
                unmet = stage.validate_prerequisites(context)
                if unmet:
                    context.state.mark_started(stage_name)
                    context.state.mark_failed(stage_name, f"Unmet prerequisites: {unmet}")
                    completed_count += 1
                    continue

                if stage.should_skip(context):
                    context.state.mark_started(stage_name)
                    context.state.mark_skipped(stage_name)
                    completed_count += 1
                    continue

                context.state.mark_started(stage_name)

            stages_executing = [s for s in stages_to_run if s in context.state.stages and context.state.stages[s].status == PipelineStatus.STARTED]

            if not stages_executing:
                continue

            if status_check_fn:
                try:
                    current_status = status_check_fn()
                    if current_status in ("cancelled", "paused"):
                        logger.info("pipeline_interrupted", job_id=job_id, status=current_status, layer=layer_idx)
                        context.state.errors.append({
                            "stage": f"layer_{layer_idx}",
                            "error": f"Pipeline {current_status} by user",
                            "duration_ms": 0,
                        })
                        cancelled = True
                        break
                except Exception:
                    pass

            lock = threading.Lock()
            futures: dict[str, Future] = {}
            layer_start = time.monotonic()

            with pool.create_executor() as executor:
                for stage_name in stages_executing:
                    stage = stage_map[stage_name]
                    future = executor.submit(
                        self._execute_stage,
                        stage, context, lock, job_id, pool, stage_start=time.monotonic(),
                    )
                    futures[stage_name] = future

                for stage_name, future in futures.items():
                    try:
                        future.result(timeout=300)
                    except Exception as exc:
                        if not context.state.has_completed(stage_name):
                            context.state.mark_failed(stage_name, str(exc))
                            context.state.errors.append({
                                "stage": stage_name,
                                "error": str(exc),
                                "duration_ms": 0,
                            })

            layer_elapsed = (time.monotonic() - layer_start) * 1000
            context.state.layer_timings[f"layer_{layer_idx}"] = round(layer_elapsed, 2)
            pool.metrics.layers_executed += 1

            for stage_name in stages_executing:
                completed_count += 1
                if progress_callback:
                    try:
                        pct = min(95, int((completed_count / total_stages) * 95))
                        progress_callback(job_id, pct, stage_name)
                    except Exception:
                        pass

        scheduling_overhead = (time.monotonic() - scheduling_start) * 1000
        context.state.scheduling_overhead_ms = round(scheduling_overhead, 2)
        context.state.total_duration_ms = (time.monotonic() - wall_start) * 1000
        context.state.contention_events = pool.metrics.contention_events
        context.state.finalize()

        pool.metrics.wall_time_ms = context.state.total_duration_ms
        pool.metrics.total_stages = total_stages
        pool.metrics.scheduling_overhead_ms = scheduling_overhead

        logger.info(
            "parallel_execution_complete",
            job_id=job_id,
            layers=len(layers),
            stages=total_stages,
            wall_time_ms=round(context.state.total_duration_ms, 2),
        )

        return context.state

    def _execute_stage(
        self,
        stage: PipelineStage,
        context: PipelineContext,
        lock: threading.Lock,
        job_id: str,
        pool: WorkerPool,
        stage_start: float,
    ) -> None:
        thread_id = threading.get_ident()
        timing_start = time.monotonic()

        try:
            artifact = stage.execute(context)
            elapsed = (time.monotonic() - stage_start) * 1000
            artifact.metadata.phase_duration_ms = elapsed

            with lock:
                artifact_key = self._artifact_repo.save(job_id, stage.name, artifact)
                context.set_result(stage.name, artifact)
                context.state.mark_completed(stage.name, artifact_key, artifact.metadata.artifact_id)

            timing = StageTiming(
                stage_name=stage.name,
                thread_id=thread_id,
                start_time=timing_start,
                end_time=time.monotonic(),
            )
            pool.record_stage_timing(timing)

            logger.info("stage_completed", stage=stage.name, job_id=job_id, thread_id=thread_id, duration_ms=round(timing.duration_ms, 2))

        except Exception as exc:
            elapsed = (time.monotonic() - stage_start) * 1000
            with lock:
                context.state.mark_failed(stage.name, str(exc))
                context.state.errors.append({
                    "stage": stage.name,
                    "error": str(exc),
                    "duration_ms": elapsed,
                })

            timing = StageTiming(
                stage_name=stage.name,
                thread_id=thread_id,
                start_time=timing_start,
                end_time=time.monotonic(),
            )
            pool.record_stage_timing(timing)

            logger.error("stage_failed", stage=stage.name, job_id=job_id, error=str(exc))

    def _setup_resume(
        self,
        job_id: str,
        resume_from: str,
        context: PipelineContext,
        stage_map: dict[str, PipelineStage],
    ) -> None:
        dag = DAGBuilder(self._stages).build()
        for stage in self._stages:
            if stage.name == resume_from:
                break
            context.state.mark_started(stage.name)
            context.state.mark_completed(stage.name)
            artifact = self._artifact_repo.load(job_id, stage.name)
            if artifact:
                context.set_result(stage.name, artifact)
                context.state.mark_cached(stage.name, artifact.metadata.artifact_id)
