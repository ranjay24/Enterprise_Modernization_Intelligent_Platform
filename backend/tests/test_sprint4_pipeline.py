"""Sprint 4 tests — Pipeline engine, state, context, and stages."""

from unittest.mock import patch

import pytest

# ─── Pipeline State ───

class TestPipelineStatus:
    def test_all_statuses(self):
        from app.pipeline.state import PipelineStatus
        assert PipelineStatus.PENDING.value == "pending"
        assert PipelineStatus.STARTED.value == "started"
        assert PipelineStatus.COMPLETED.value == "completed"
        assert PipelineStatus.FAILED.value == "failed"
        assert PipelineStatus.CACHED.value == "cached"
        assert PipelineStatus.SKIPPED.value == "skipped"
        assert PipelineStatus.RETRYING.value == "retrying"


class TestStageState:
    def test_defaults(self):
        from app.pipeline.state import PipelineStatus, StageState
        s = StageState()
        assert s.stage_name == ""
        assert s.status == PipelineStatus.PENDING
        assert s.error is None
        assert s.tokens_used == 0

    def test_to_dict_roundtrip(self):
        from app.pipeline.state import PipelineStatus, StageState
        s = StageState(stage_name="s1", status=PipelineStatus.COMPLETED, duration_ms=1500.0)
        d = s.to_dict()
        assert d["stage_name"] == "s1"
        assert d["status"] == "completed"
        s2 = StageState.from_dict(d)
        assert s2.stage_name == "s1"
        assert s2.status == PipelineStatus.COMPLETED
        assert s2.duration_ms == 1500.0


class TestPipelineState:
    def test_initial_state(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        assert ps.job_id == "job-001"
        assert ps.status == "pending"
        assert ps.stages == {}

    def test_mark_started(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.mark_started("stage_a")
        assert ps.status == "running"
        assert ps.current_stage == "stage_a"
        assert "stage_a" in ps.stages
        assert ps.stages["stage_a"].status.value == "started"

    def test_mark_completed(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.mark_started("stage_a")
        ps.mark_completed("stage_a", artifact_key="key1", artifact_id="art1")
        assert ps.stages["stage_a"].status.value == "completed"
        assert ps.stages["stage_a"].artifact_key == "key1"
        assert ps.total_artifacts == 1

    def test_mark_failed(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.mark_started("stage_a")
        ps.mark_failed("stage_a", "error msg")
        assert ps.stages["stage_a"].status.value == "failed"
        assert ps.stages["stage_a"].error == "error msg"
        assert len(ps.errors) == 1

    def test_mark_skipped(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.mark_started("stage_a")
        ps.mark_skipped("stage_a")
        assert ps.stages["stage_a"].status.value == "skipped"

    def test_mark_cached(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.mark_started("stage_a")
        ps.mark_cached("stage_a", artifact_key="cached_key")
        assert ps.stages["stage_a"].status.value == "cached"

    def test_has_completed(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.mark_started("stage_a")
        assert ps.has_completed("stage_a") is False
        ps.mark_completed("stage_a")
        assert ps.has_completed("stage_a") is True

    def test_finalize(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.mark_started("stage_a")
        ps.mark_completed("stage_a")
        ps.finalize()
        assert ps.status == "completed"
        assert ps.completed_at is not None

    def test_finalize_with_errors(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.mark_started("stage_a")
        ps.mark_failed("stage_a", "err")
        ps.finalize()
        assert ps.status == "completed_with_errors"

    def test_finalize_failed(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.finalize_failed("fatal error")
        assert ps.status == "failed"

    def test_to_dict_roundtrip(self):
        from app.pipeline.state import PipelineState
        ps = PipelineState(job_id="job-001")
        ps.mark_started("stage_a")
        ps.mark_completed("stage_a", artifact_key="k1")
        d = ps.to_dict()
        ps2 = PipelineState.from_dict(d)
        assert ps2.job_id == "job-001"
        assert "stage_a" in ps2.stages
        assert ps2.stages["stage_a"].artifact_key == "k1"


# ─── Pipeline Context ───

class TestPipelineContext:
    def test_set_get_result(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.context import PipelineContext
        ctx = PipelineContext(job_id="j1")
        art = Artifact(metadata=ArtifactMetadata(artifact_type="test"), content={"k": "v"})
        ctx.set_result("stage_a", art)
        assert ctx.get_result("stage_a") is art
        assert ctx.get_result("stage_b") is None

    def test_get_result_data(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.context import PipelineContext
        ctx = PipelineContext(job_id="j1")
        art = Artifact(metadata=ArtifactMetadata(), content={"data": 42})
        ctx.set_result("s1", art)
        assert ctx.get_result_data("s1") == {"data": 42}
        assert ctx.get_result_data("missing") == {}

    def test_to_dict(self):
        from app.pipeline.context import PipelineContext
        ctx = PipelineContext(job_id="j1", data={"input": "file.zip"})
        d = ctx.to_dict()
        assert d["job_id"] == "j1"
        assert "input" in d["data_keys"]


# ─── Pipeline Stage ABC ───

class TestPipelineStageABC:
    def test_cannot_instantiate(self):
        from app.pipeline.stage import PipelineStage
        with pytest.raises(TypeError):
            PipelineStage()

    def test_concrete_stage(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.context import PipelineContext
        from app.pipeline.stage import PipelineStage

        class DummyStage(PipelineStage):
            @property
            def name(self):
                return "dummy"

            @property
            def phase(self):
                return "static_analysis"

            def execute(self, context):
                return Artifact(
                    metadata=ArtifactMetadata(artifact_type="dummy"),
                    content={"result": "ok"},
                )

        stage = DummyStage()
        assert stage.name == "dummy"
        assert stage.phase == "static_analysis"
        assert stage.requires_ai is False

        ctx = PipelineContext(job_id="j1")
        artifact = stage.execute(ctx)
        assert artifact.content["result"] == "ok"

    def test_validate_prerequisites_default(self):
        from app.pipeline.context import PipelineContext
        from app.pipeline.stage import PipelineStage

        class NoPrereqStage(PipelineStage):
            @property
            def name(self): return "np"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(), content={})

        ctx = PipelineContext(job_id="j1")
        assert NoPrereqStage().validate_prerequisites(ctx) == []

    def test_should_skip_default(self):
        from app.pipeline.context import PipelineContext
        from app.pipeline.stage import PipelineStage

        class NeverSkipStage(PipelineStage):
            @property
            def name(self): return "ns"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(), content={})

        ctx = PipelineContext(job_id="j1")
        assert NeverSkipStage().should_skip(ctx) is False


# ─── Pipeline Engine ───

class TestPipelineEngine:
    def test_execute_single_stage(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.engine import PipelineEngine
        from app.pipeline.stage import PipelineStage

        class SimpleStage(PipelineStage):
            @property
            def name(self): return "simple"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(
                    metadata=ArtifactMetadata(artifact_type="simple"),
                    content={"output": "done"},
                )

        with patch("app.pipeline.engine.ArtifactRepository"):
            engine = PipelineEngine(stages=[SimpleStage()])
            state = engine.execute("job-001")
            assert state.status == "completed"
            assert "simple" in state.stages
            assert state.stages["simple"].status.value == "completed"

    def test_execute_stage_failure(self):
        from app.pipeline.engine import PipelineEngine
        from app.pipeline.stage import PipelineStage

        class FailStage(PipelineStage):
            @property
            def name(self): return "fail"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                raise RuntimeError("boom")

        with patch("app.pipeline.engine.ArtifactRepository"):
            engine = PipelineEngine(stages=[FailStage()])
            state = engine.execute("job-001")
            assert state.status == "completed_with_errors"
            assert state.stages["fail"].status.value == "failed"
            assert "boom" in state.stages["fail"].error

    def test_execute_skip_stage(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.engine import PipelineEngine
        from app.pipeline.stage import PipelineStage

        class SkipStage(PipelineStage):
            @property
            def name(self): return "skip_me"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(), content={})
            def should_skip(self, ctx):
                return True

        with patch("app.pipeline.engine.ArtifactRepository"):
            engine = PipelineEngine(stages=[SkipStage()])
            state = engine.execute("job-001")
            assert state.stages["skip_me"].status.value == "skipped"

    def test_stages_property(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.engine import PipelineEngine
        from app.pipeline.stage import PipelineStage

        class S1(PipelineStage):
            @property
            def name(self): return "s1"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx): return Artifact(metadata=ArtifactMetadata(), content={})

        class S2(PipelineStage):
            @property
            def name(self): return "s2"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx): return Artifact(metadata=ArtifactMetadata(), content={})

        with patch("app.pipeline.engine.ArtifactRepository"):
            engine = PipelineEngine(stages=[S1(), S2()])
            assert engine.stage_names == ["s1", "s2"]
