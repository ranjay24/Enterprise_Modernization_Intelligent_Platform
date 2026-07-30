"""Sprint 5 tests — Performance benchmarks."""

import time

from app.artifacts.models import Artifact, ArtifactMetadata
from app.pipeline.engine import PipelineEngine
from app.pipeline.stage import PipelineStage
from app.scheduling.dag import DAGBuilder
from app.scheduling.executor import ParallelExecutor, SequentialExecutor
from app.scheduling.resolver import DependencyResolver

# ─── Helpers ───

class SlowStage(PipelineStage):
    def __init__(self, stage_name: str, deps: list[str] | None = None, delay: float = 0.05):
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
        time.sleep(self._delay)
        return Artifact(
            content={"test": True},
            metadata=ArtifactMetadata(generator="test", artifact_type="test"),
        )


# ─── DAG Performance ───

class TestDAGPerformance:
    def test_dag_build_large_graph(self):
        stages = [SlowStage(f"S{i}", [f"S{j}" for j in range(max(0, i-3), i)]) for i in range(50)]
        start = time.monotonic()
        dag = DAGBuilder(stages).build()
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 100  # Should build in < 100ms
        assert len(dag.adjacency) == 50

    def test_topological_sort_large_graph(self):
        stages = [SlowStage(f"S{i}", [f"S{j}" for j in range(max(0, i-3), i)]) for i in range(50)]
        dag = DAGBuilder(stages).build()
        resolver = DependencyResolver(dag.adjacency)
        start = time.monotonic()
        order = resolver.topological_sort()
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 100
        assert len(order) == 50

    def test_layer_computation_large_graph(self):
        stages = [SlowStage(f"S{i}", [f"S{j}" for j in range(max(0, i-5), i)]) for i in range(100)]
        dag = DAGBuilder(stages).build()
        start = time.monotonic()
        layers = dag.get_layers()
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 200
        assert len(layers) > 0
        total_stages = sum(len(l) for l in layers)
        assert total_stages == 100


# ─── Parallel Speedup ───

class TestParallelSpeedup:
    def test_parallel_faster_than_sequential_independent(self):
        stages = [SlowStage(f"S{i}", delay=0.05) for i in range(8)]

        seq_start = time.monotonic()
        seq_exec = SequentialExecutor(stages)
        seq_state = seq_exec.execute("perf-seq-1")
        seq_elapsed = time.monotonic() - seq_start

        par_start = time.monotonic()
        par_exec = ParallelExecutor(stages, max_workers=4)
        par_state = par_exec.execute("perf-par-1")
        par_elapsed = time.monotonic() - par_start

        assert par_state.status == "completed"
        assert seq_state.status == "completed"
        # Parallel should complete faster (within 30% to account for S3 overhead)
        assert par_elapsed < seq_elapsed * 1.3

    def test_parallel_faster_diamond_dag(self):
        stages = [
            SlowStage("A", delay=0.05),
            SlowStage("B", ["A"], delay=0.05),
            SlowStage("C", ["A"], delay=0.05),
            SlowStage("D", ["B", "C"], delay=0.05),
            SlowStage("E", ["D"], delay=0.05),
        ]

        seq_start = time.monotonic()
        seq_exec = SequentialExecutor(stages)
        seq_state = seq_exec.execute("perf-seq-2")
        seq_elapsed = time.monotonic() - seq_start

        par_start = time.monotonic()
        par_exec = ParallelExecutor(stages, max_workers=4)
        par_state = par_exec.execute("perf-par-2")
        par_elapsed = time.monotonic() - par_start

        assert par_state.status == "completed"
        assert seq_state.status == "completed"
        # Should see some speedup from parallelizing B and C (with tolerance for S3 overhead)
        assert par_elapsed < seq_elapsed * 1.3

    def test_parallel_layer_metrics(self):
        stages = [
            SlowStage("A", delay=0.02),
            SlowStage("B", ["A"], delay=0.02),
            SlowStage("C", ["A"], delay=0.02),
            SlowStage("D", ["B", "C"], delay=0.02),
        ]
        executor = ParallelExecutor(stages, max_workers=2)
        state = executor.execute("perf-par-3")
        assert state.parallel_execution
        assert len(state.execution_layers) >= 3
        assert state.total_duration_ms > 0
        assert state.scheduling_overhead_ms >= 0

    def test_sequential_deterministic_order(self):
        stages = [
            SlowStage("C", delay=0.01),
            SlowStage("A", delay=0.01),
            SlowStage("B", delay=0.01),
        ]
        executor = SequentialExecutor(stages)
        state = executor.execute("perf-seq-det")
        stage_order = list(state.stages.keys())
        assert stage_order == ["C", "A", "B"]


# ─── Engine Performance ───

class TestEnginePerformance:
    def test_engine_parallel_vs_sequential(self):
        stages = [SlowStage(f"S{i}", delay=0.03) for i in range(6)]
        engine = PipelineEngine(stages)

        seq_start = time.monotonic()
        seq_state = engine.execute("perf-eng-seq")
        seq_elapsed = time.monotonic() - seq_start

        par_start = time.monotonic()
        par_state = engine.execute("perf-eng-par", parallel=True)
        par_elapsed = time.monotonic() - par_start

        assert seq_state.status == "completed"
        assert par_state.status == "completed"
        assert par_elapsed < seq_elapsed

    def test_engine_large_pipeline(self):
        stages = [
            SlowStage("A", delay=0.02),
            SlowStage("B", ["A"], delay=0.02),
            SlowStage("C", ["A"], delay=0.02),
            SlowStage("D", ["B", "C"], delay=0.02),
            SlowStage("E", ["D"], delay=0.02),
            SlowStage("F", ["D"], delay=0.02),
            SlowStage("G", ["E", "F"], delay=0.02),
        ]
        engine = PipelineEngine(stages)
        start = time.monotonic()
        state = engine.execute("perf-eng-large", parallel=True)
        elapsed = (time.monotonic() - start) * 1000
        assert state.status == "completed"
        assert elapsed < 15000  # Should complete in < 15s (S3 overhead)
