"""Sprint 5 tests — Full pipeline compatibility with strategy pattern."""

import threading
from unittest.mock import MagicMock

from app.artifacts.models import Artifact, ArtifactMetadata
from app.pipeline.context import PipelineContext
from app.pipeline.engine import PipelineEngine
from app.pipeline.stage import PipelineStage
from app.pipeline.state import PipelineState, PipelineStatus

# ─── Helpers ───

class DummyStage(PipelineStage):
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
        raise RuntimeError(f"Stage {self._name} failed")


# ─── PipelineEngine Strategy Pattern ───

class TestPipelineEngineStrategy:
    def test_default_sequential(self):
        stages = [DummyStage("A"), DummyStage("B")]
        engine = PipelineEngine(stages)
        assert not engine._parallel

    def test_parallel_mode(self):
        stages = [DummyStage("A"), DummyStage("B")]
        engine = PipelineEngine(stages, parallel=True)
        assert engine._parallel

    def test_execute_sequential_mode(self):
        stages = [DummyStage("A"), DummyStage("B")]
        engine = PipelineEngine(stages, parallel=False)
        state = engine.execute("job-300")
        assert state.status == "completed"
        assert not state.parallel_execution

    def test_execute_parallel_mode(self):
        stages = [DummyStage("A"), DummyStage("B")]
        engine = PipelineEngine(stages, parallel=True, max_workers=2)
        state = engine.execute("job-301")
        assert state.status == "completed"
        assert state.parallel_execution

    def test_override_parallel_in_execute(self):
        stages = [DummyStage("A"), DummyStage("B")]
        engine = PipelineEngine(stages, parallel=False)
        state = engine.execute("job-302", parallel=True)
        assert state.status == "completed"
        assert state.parallel_execution

    def test_override_parallel_in_execute_to_false(self):
        stages = [DummyStage("A"), DummyStage("B")]
        engine = PipelineEngine(stages, parallel=True)
        state = engine.execute("job-303", parallel=False)
        assert state.status == "completed"
        assert not state.parallel_execution

    def test_both_modes_same_results(self):
        stages = [
            DummyStage("A"),
            DummyStage("B", ["A"]),
            DummyStage("C", ["A"]),
        ]
        engine = PipelineEngine(stages)
        state_seq = engine.execute("job-304a")
        state_par = engine.execute("job-304b", parallel=True)
        assert state_seq.status == state_par.status
        assert set(state_seq.stages.keys()) == set(state_par.stages.keys())
        for name in state_seq.stages:
            assert state_seq.stages[name].status == state_par.stages[name].status

    def test_progress_callback_both_modes(self):
        stages = [DummyStage("A"), DummyStage("B")]
        cb_seq = MagicMock()
        cb_par = MagicMock()
        engine = PipelineEngine(stages)
        engine.execute("job-305a", progress_callback=cb_seq)
        engine.execute("job-305b", progress_callback=cb_par, parallel=True)
        assert cb_seq.call_count == cb_par.call_count

    def test_failing_stage_both_modes(self):
        stages = [DummyStage("A"), FailingStage("B"), DummyStage("C")]
        engine = PipelineEngine(stages)
        state_seq = engine.execute("job-306a")
        state_par = engine.execute("job-306b", parallel=True)
        assert state_seq.has_completed("A") == state_par.has_completed("A")
        assert state_seq.stages["B"].status == PipelineStatus.FAILED
        assert state_par.stages["B"].status == PipelineStatus.FAILED


# ─── PipelineState Sprint 5 Fields ───

class TestPipelineStateSprint5:
    def test_default_sprint5_fields(self):
        state = PipelineState(job_id="job-400")
        assert state.parallel_execution is False
        assert state.execution_layers == []
        assert state.max_concurrency == 1
        assert state.contention_events == 0
        assert state.scheduling_overhead_ms == 0.0
        assert state.layer_timings == {}

    def test_to_dict_sprint5_fields(self):
        state = PipelineState(
            job_id="job-401",
            parallel_execution=True,
            execution_layers=[["A"], ["B", "C"]],
            max_concurrency=4,
            contention_events = 2,
            scheduling_overhead_ms=15.5,
            layer_timings={"layer_0": 10.0, "layer_1": 5.5},
        )
        d = state.to_dict()
        assert d["parallel_execution"] is True
        assert d["execution_layers"] == [["A"], ["B", "C"]]
        assert d["max_concurrency"] == 4
        assert d["contention_events"] == 2
        assert d["scheduling_overhead_ms"] == 15.5
        assert d["layer_timings"] == {"layer_0": 10.0, "layer_1": 5.5}

    def test_from_dict_sprint5_fields(self):
        data = {
            "job_id": "job-402",
            "parallel_execution": True,
            "execution_layers": [["A"], ["B"]],
            "max_concurrency": 2,
            "contention_events": 1,
            "scheduling_overhead_ms": 8.3,
            "layer_timings": {"layer_0": 5.0},
        }
        state = PipelineState.from_dict(data)
        assert state.parallel_execution is True
        assert state.execution_layers == [["A"], ["B"]]
        assert state.max_concurrency == 2
        assert state.contention_events == 1
        assert state.scheduling_overhead_ms == 8.3
        assert state.layer_timings == {"layer_0": 5.0}

    def test_from_dict_missing_sprint5_fields(self):
        state = PipelineState.from_dict({"job_id": "job-403"})
        assert state.parallel_execution is False
        assert state.execution_layers == []
        assert state.max_concurrency == 1


# ─── PipelineContext Thread Safety ───

class TestPipelineContextThreadSafety:
    def test_lock_exists(self):
        ctx = PipelineContext(job_id="job-500")
        assert hasattr(ctx, '_lock')
        lock_type = type(threading.Lock())
        assert isinstance(ctx._lock, lock_type)

    def test_set_get_result_thread_safe(self):
        ctx = PipelineContext(job_id="job-501")

    def test_set_get_result_thread_safe(self):
        ctx = PipelineContext(job_id="job-501")
        artifact = Artifact(
            content={"value": 1},
            metadata=ArtifactMetadata(generator="test", artifact_type="test"),
        )
        ctx.set_result("test", artifact)
        result = ctx.get_result("test")
        assert result is not None
        assert result.content["value"] == 1


# ─── Depends On Property ───

class TestDependsOnProperty:
    def test_extraction_has_no_deps(self):
        from app.pipeline.stages.extraction import ExtractionStage
        stage = ExtractionStage()
        assert stage.depends_on == []

    def test_static_analysis_depends_on_extraction(self):
        from app.pipeline.stages.static_analysis import StaticAnalysisStage
        stage = StaticAnalysisStage()
        assert stage.depends_on == ["extraction"]

    def test_ai_boundaries_depends_on_two(self):
        from app.pipeline.stages.ai_boundaries import AIBoundariesStage
        stage = AIBoundariesStage()
        assert "static_analysis" in stage.depends_on
        assert "enterprise_analysis" in stage.depends_on

    def test_ai_adrs_depends_on_three(self):
        from app.pipeline.stages.ai_adrs import AIADRStage
        stage = AIADRStage()
        assert "static_analysis" in stage.depends_on
        assert "enterprise_analysis" in stage.depends_on
        assert "ai_boundaries" in stage.depends_on

    def test_results_assembly_depends_on_all_ai(self):
        from app.pipeline.stages.results_assembly import ResultsAssemblyStage
        stage = ResultsAssemblyStage()
        assert len(stage.depends_on) == 8
        assert "ai_explainability" in stage.depends_on

    def test_report_generation_depends_on_results(self):
        from app.pipeline.stages.report_generation import ReportGenerationStage
        stage = ReportGenerationStage()
        assert stage.depends_on == ["results_assembly"]

    def test_manifest_depends_on_results(self):
        from app.pipeline.stages.manifest import ManifestStage
        stage = ManifestStage()
        assert stage.depends_on == ["results_assembly"]

    def test_all_stages_have_depends_on(self):
        from app.pipeline.stages.ai_adrs import AIADRStage
        from app.pipeline.stages.ai_boundaries import AIBoundariesStage
        from app.pipeline.stages.ai_cost import AICostStage
        from app.pipeline.stages.ai_explainability import AIExplainabilityStage
        from app.pipeline.stages.ai_migration import AIMigrationStage
        from app.pipeline.stages.ai_readiness import AIReadinessStage
        from app.pipeline.stages.enterprise_analysis import EnterpriseAnalysisStage
        from app.pipeline.stages.extraction import ExtractionStage
        from app.pipeline.stages.manifest import ManifestStage
        from app.pipeline.stages.report_generation import ReportGenerationStage
        from app.pipeline.stages.results_assembly import ResultsAssemblyStage
        from app.pipeline.stages.static_analysis import StaticAnalysisStage

        all_stages = [
            ExtractionStage(), StaticAnalysisStage(), EnterpriseAnalysisStage(),
            AIBoundariesStage(), AIReadinessStage(), AIADRStage(),
            AIMigrationStage(), AICostStage(), AIExplainabilityStage(),
            ResultsAssemblyStage(), ReportGenerationStage(), ManifestStage(),
        ]
        for stage in all_stages:
            assert isinstance(stage.depends_on, list), f"{stage.name} missing depends_on"
