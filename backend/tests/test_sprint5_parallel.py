"""Sprint 5 tests — Parallel execution + thread safety."""

import threading
import time
from unittest.mock import MagicMock

from app.artifacts.models import Artifact, ArtifactMetadata
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage
from app.scheduling.executor import ParallelExecutor, SequentialExecutor
from app.scheduling.pool import StageTiming, WorkerPool

# ─── Helpers ───

class DummyStage(PipelineStage):
    def __init__(self, stage_name: str, deps: list[str] | None = None, delay: float = 0.0):
        self._name = stage_name
        self._deps = deps
        self._delay = delay

    @property
    def name(self):
        return self._name

    @property
    def phase(self):
        return self._name

    @property
    def depends_on(self):
        return self._deps if self._deps is not None else None

    def execute(self, context):
        if self._delay > 0:
            time.sleep(self._delay)
        return Artifact(
            content={"test": True, "stage": self._name},
            metadata=ArtifactMetadata(generator="test", artifact_type="test"),
        )


class FailingStage(PipelineStage):
    def __init__(self, stage_name: str, deps: list[str] | None = None):
        self._name = stage_name
        self._deps = deps

    @property
    def name(self):
        return self._name

    @property
    def phase(self):
        return self._name

    @property
    def depends_on(self):
        return self._deps if self._deps is not None else None

    def execute(self, context):
        raise RuntimeError(f"Stage {self._name} failed intentionally")


# ─── Sequential Executor ───

class TestSequentialExecutor:
    def test_execute_empty(self):
        executor = SequentialExecutor([])
        state = executor.execute("job-001")
        assert state.status == "completed"
        assert state.total_artifacts == 0

    def test_execute_single_stage(self):
        stages = [DummyStage("extraction")]
        executor = SequentialExecutor(stages)
        state = executor.execute("job-002")
        assert state.status == "completed"
        assert state.has_completed("extraction")

    def test_execute_linear_chain(self):
        stages = [
            DummyStage("A", []),
            DummyStage("B", ["A"]),
            DummyStage("C", ["B"]),
        ]
        executor = SequentialExecutor(stages)
        state = executor.execute("job-003")
        assert state.status == "completed"
        assert state.has_completed("A")
        assert state.has_completed("B")
        assert state.has_completed("C")

    def test_execute_with_progress_callback(self):
        stages = [DummyStage("A"), DummyStage("B")]
        callback = MagicMock()
        executor = SequentialExecutor(stages)
        executor.execute("job-004", progress_callback=callback)
        assert callback.call_count == 4

    def test_execute_with_failing_stage(self):
        stages = [
            DummyStage("A"),
            FailingStage("B"),
            DummyStage("C"),
        ]
        executor = SequentialExecutor(stages)
        state = executor.execute("job-005")
        assert state.has_completed("A")
        assert state.has_completed("C")

    def test_parallel_false_by_default(self):
        executor = SequentialExecutor([DummyStage("A")])
        state = executor.execute("job-006")
        assert not state.parallel_execution

    def test_resume_from_stage(self):
        stages = [
            DummyStage("A"),
            DummyStage("B"),
            DummyStage("C"),
        ]
        executor = SequentialExecutor(stages)
        state = executor.execute("job-007", resume_from="B")
        assert state.has_completed("A")


# ─── Parallel Executor ───

class TestParallelExecutor:
    def test_execute_empty(self):
        executor = ParallelExecutor([])
        state = executor.execute("job-100")
        assert state.status == "completed"
        assert state.parallel_execution

    def test_execute_independent_stages(self):
        stages = [
            DummyStage("A"),
            DummyStage("B"),
            DummyStage("C"),
        ]
        executor = ParallelExecutor(stages, max_workers=2)
        state = executor.execute("job-101")
        assert state.status == "completed"
        assert state.has_completed("A")
        assert state.has_completed("B")
        assert state.has_completed("C")
        assert state.parallel_execution

    def test_execute_respects_dependencies(self):
        stages = [
            DummyStage("A", []),
            DummyStage("B", ["A"]),
        ]
        executor = ParallelExecutor(stages, max_workers=2)
        state = executor.execute("job-102")
        assert state.status == "completed"
        assert state.has_completed("A")
        assert state.has_completed("B")

    def test_execute_diamond_dag(self):
        stages = [
            DummyStage("A", []),
            DummyStage("B", ["A"]),
            DummyStage("C", ["A"]),
            DummyStage("D", ["B", "C"]),
        ]
        executor = ParallelExecutor(stages, max_workers=4)
        state = executor.execute("job-103")
        assert state.status == "completed"
        assert state.has_completed("D")
        assert len(state.execution_layers) > 0

    def test_parallel_execution_metrics(self):
        stages = [
            DummyStage("A", []),
            DummyStage("B", []),
            DummyStage("C", ["A", "B"]),
        ]
        executor = ParallelExecutor(stages, max_workers=2)
        state = executor.execute("job-104")
        assert state.parallel_execution
        assert state.max_concurrency == 2
        assert len(state.execution_layers) > 0
        assert state.total_duration_ms > 0

    def test_execute_with_failing_stage(self):
        stages = [
            DummyStage("A"),
            FailingStage("B"),
            DummyStage("C", ["A"]),
        ]
        executor = ParallelExecutor(stages, max_workers=2)
        state = executor.execute("job-105")
        assert state.has_completed("A")

    def test_max_concurrency_limits_workers(self):
        stages = [DummyStage(f"S{i}") for i in range(8)]
        executor = ParallelExecutor(stages, max_workers=2)
        state = executor.execute("job-106")
        assert state.max_concurrency == 2
        assert state.status == "completed"


# ─── Worker Pool ───

class TestWorkerPool:
    def test_create_executor(self):
        pool = WorkerPool(max_workers=2)
        with pool.create_executor() as executor:
            future = executor.submit(lambda: 42)
            assert future.result() == 42

    def test_metrics(self):
        pool = WorkerPool(max_workers=2)
        timing = StageTiming(
            stage_name="test",
            thread_id=threading.get_ident(),
            start_time=time.monotonic(),
            end_time=time.monotonic() + 0.1,
        )
        pool.record_stage_timing(timing)
        assert pool.metrics.total_stages == 0  # record_stage_timing doesn't increment total_stages
        assert len(pool.metrics.stage_timings) == 1

    def test_contention_detection(self):
        pool = WorkerPool(max_workers=2)
        pool.record_contention()
        pool.record_contention()
        assert pool.metrics.contention_events == 2

    def test_avg_parallelism(self):
        pool = WorkerPool(max_workers=2)
        pool.metrics.wall_time_ms = 100.0
        timing = StageTiming(
            stage_name="test",
            thread_id=threading.get_ident(),
            start_time=0.0,
            end_time=0.1,
        )
        pool.record_stage_timing(timing)
        assert pool.metrics.avg_parallelism > 0


# ─── Thread Safety ───

class TestThreadSafety:
    def test_concurrent_set_result(self):
        context = PipelineContext(job_id="job-200")
        errors = []

        def writer(stage_name):
            try:
                artifact = Artifact(
                    content={"value": stage_name},
                    metadata=ArtifactMetadata(generator="test", artifact_type="test"),
                )
                context.set_result(stage_name, artifact)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"stage_{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(context.results) == 20

    def test_concurrent_read_write(self):
        context = PipelineContext(job_id="job-201")
        artifact = Artifact(
            content={"value": 0},
            metadata=ArtifactMetadata(generator="test", artifact_type="test"),
        )
        context.set_result("shared", artifact)
        errors = []

        def reader():
            try:
                for _ in range(50):
                    result = context.get_result("shared")
                    _ = result.content if result else None
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(50):
                    a = Artifact(
                        content={"value": i},
                        metadata=ArtifactMetadata(generator="test", artifact_type="test"),
                    )
                    context.set_result("shared", a)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(5)] + \
                  [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
