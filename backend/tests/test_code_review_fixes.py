"""Regression tests for P0/P1 security and correctness fixes from the
external 47-item EMIP code review (uncommitted work)."""

import io
import os
import zipfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.analysis.contracts.context import AnalysisContext
from app.analysis.metrics.code_metrics import CodeMetricsAnalyzer
from app.analysis.metrics.quality import QualityMetricsAnalyzer
from app.analysis.parser.java_parser import JavaParser
from app.analysis.rules.boundary_rules import BoundaryRule, SingleOwnershipRule
from app.ai.cost.tracker import AICostTracker
from app.ai.provider.adapter import AIModelRequest, AIModelResponse
from app.ai.provider.config import AIModelConfig, AIProviderConfig
from app.ai.provider.nova import NovaAdapter
from app.ai.provider.registry import ProviderRegistry
from app.ai.validation.validator import AIResponseValidator
from app.artifacts.models import Artifact, ArtifactMetadata
from app.exceptions.custom import ValidationFailedException
from app.pipeline.context import PipelineContext
from app.pipeline.state import PipelineState
from app.pipeline.stage import PipelineStage
from app.scheduling.executor import ParallelExecutor, SequentialExecutor
from app.services.static_analyzer import _parse_java_classes
from app.utils.zip_utils import (
    ZipSafetyError,
    cleanup_temp_dir,
    extract_zip_to_temp,
    validate_zip_safety,
)
from app.validators.zip_validator import validate_zip_file


# ─── Helpers ───

def _make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


class DummyStage(PipelineStage):
    def __init__(self, stage_name: str):
        self._name = stage_name

    @property
    def name(self):
        return self._name

    @property
    def phase(self):
        return self._name

    def execute(self, context):
        return Artifact(
            content={"test": True, "stage": self._name},
            metadata=ArtifactMetadata(generator="test", artifact_type="test"),
        )


class FailingStage(PipelineStage):
    def __init__(self, stage_name: str):
        self._name = stage_name

    @property
    def name(self):
        return self._name

    @property
    def phase(self):
        return self._name

    def execute(self, context):
        raise RuntimeError("boom")


# ─── #1/#2 ZIP path traversal + zip-bomb caps ───

class TestZipSafety:
    def test_extract_zip_rejects_path_traversal(self):
        payload = _make_zip({"../evil.txt": b"pwned"})
        assert extract_zip_to_temp(payload) is None

    def test_extract_zip_rejects_absolute_path(self):
        payload = _make_zip({"/etc/evil.txt": b"pwned"})
        assert extract_zip_to_temp(payload) is None

    def test_validate_zip_safety_rejects_traversal_member(self):
        payload = _make_zip({"../evil.txt": b"pwned"})
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            with pytest.raises(ZipSafetyError):
                validate_zip_safety(zf)

    def test_validate_zip_safety_rejects_compression_bomb(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("zeros.bin", b"\x00" * (300 * 1024))
        payload = buf.getvalue()
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            with pytest.raises(ZipSafetyError):
                validate_zip_safety(zf)

    def test_validate_zip_safety_rejects_too_many_entries(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for i in range(10001):
                zf.writestr(f"file_{i}.txt", b"x")
        payload = buf.getvalue()
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            with pytest.raises(ZipSafetyError):
                validate_zip_safety(zf)

    def test_zip_validator_rejects_unsafe_payload(self):
        with pytest.raises(ValidationFailedException):
            validate_zip_file("proj.zip", _make_zip({"../evil.txt": b"x"}))

    def test_extract_zip_accepts_normal_payload(self):
        payload = _make_zip({"src/Main.java": b"class Main {}"})
        extracted = extract_zip_to_temp(payload)
        assert extracted is not None
        try:
            assert os.path.isfile(os.path.join(extracted, "src", "Main.java"))
        finally:
            cleanup_temp_dir(extracted)


# ─── #16 get_result_data must not leak the live reference ───

class TestPipelineContextCopy:
    def test_get_result_data_returns_deep_copy(self):
        ctx = PipelineContext(job_id="j1")
        ctx.set_result("s1", Artifact(metadata=ArtifactMetadata(), content={"data": {"n": 1}}))
        got = ctx.get_result_data("s1")
        got["data"]["n"] = 999
        assert ctx.get_result("s1").content["data"]["n"] == 1


# ─── #19 idempotent artifact counting in state ───

class TestPipelineStateCounting:
    def test_mark_completed_counts_artifact_once(self):
        ps = PipelineState(job_id="j1")
        ps.mark_started("a")
        ps.mark_completed("a", "k1", "id1")
        ps.mark_completed("a", "k2", "id2")
        assert ps.total_artifacts == 1

    def test_mark_cached_counts_artifact_once(self):
        ps = PipelineState(job_id="j2")
        ps.mark_started("b")
        ps.mark_cached("b", "k1")
        ps.mark_cached("b", "k2")
        assert ps.total_artifacts == 1

    def test_mark_completed_after_cached_counts_once(self):
        ps = PipelineState(job_id="j3")
        ps.mark_started("c")
        ps.mark_cached("c", "k1")
        ps.mark_completed("c", "k2", "id2")
        assert ps.total_artifacts == 1


# ─── #11 validator must tolerate non-numeric confidence ───

class TestValidatorTolerance:
    def test_non_numeric_confidence_does_not_crash(self):
        v = AIResponseValidator()
        res = v.validate(
            '{"confidence": "high", "recommendations": [{"confidence": "N/A", "title": "t"}]}'
        )
        assert res.is_valid is True
        assert res.confidence_score == 0.0


# ─── #14 cost tracker / registry job_id wiring ───

class TestCostTracking:
    def test_estimate_cost_honors_updated_profile(self):
        AICostTracker().update_cost_profile("test-model-x", input_cost_per_1k=1.0, output_cost_per_1k=2.0)
        assert AICostTracker.estimate_cost(1000, 1000, "test-model-x") == 3.0

    def test_registry_invoke_tracks_job_usage(self):
        config = AIProviderConfig(
            models=[AIModelConfig(model_id="amazon.nova-pro-v1:0", provider="bedrock")],
            default_model_id="amazon.nova-pro-v1:0",
            fallback_model_id="amazon.nova-lite-v1:0",
        )
        stub = MagicMock()
        stub.invoke.return_value = AIModelResponse(
            text="ok", model_id="amazon.nova-pro-v1:0", input_tokens=10, output_tokens=5
        )
        with patch(
            "app.ai.provider.registry.ProviderFactory.create_from_provider_config",
            return_value=stub,
        ):
            registry = ProviderRegistry(config)
            resp = registry.invoke(AIModelRequest(prompt="hi", metadata={"job_id": "job-42"}))
            assert resp.success
            usage = registry.cost_tracker.get_job_usage("job-42")
            assert usage["invocations"] == 1
            assert usage["total_input_tokens"] == 10
            assert usage["by_model"]["amazon.nova-pro-v1:0"]["count"] == 1


# ─── #13 Nova system prompt + temperature passthrough ───

class _FakeBedrock:
    def __init__(self):
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "output": {"message": {"content": [{"text": "ok"}]}},
            "usage": {"inputTokens": 10, "outputTokens": 5},
            "stopReason": "end_turn",
        }


def _nova_adapter():
    config = AIModelConfig(model_id="amazon.nova-lite-v1:0", provider="bedrock", temperature=0.7)
    with patch("app.ai.provider.nova.get_settings", return_value=MagicMock()):
        adapter = NovaAdapter(config)
    fake = _FakeBedrock()
    adapter._clients = SimpleNamespace(bedrock=fake)
    return adapter, fake


class TestNovaAdapter:
    def test_sends_system_prompt_and_honors_explicit_zero_temp(self):
        adapter, fake = _nova_adapter()
        resp = adapter.invoke(AIModelRequest(prompt="hi", system_prompt="be concise", temperature=0.0))
        assert resp.text == "ok"
        call = fake.calls[0]
        assert call["messages"][0]["role"] == "system"
        assert call["messages"][0]["content"][0]["text"] == "be concise"
        assert call["messages"][1]["role"] == "user"
        assert call["inferenceConfig"]["temperature"] == 0.0

    def test_defaults_temperature_to_config(self):
        adapter, fake = _nova_adapter()
        adapter.invoke(AIModelRequest(prompt="hi"))
        assert fake.calls[0]["inferenceConfig"]["temperature"] == 0.7


# ─── #23/#28 parser complexity, method spans, duplication ───

class TestJavaParserMetrics:
    def test_counts_cyclomatic_complexity_and_method_spans(self):
        src = """
public class Demo {
    public void decisionHeavy() {
        if (x > 0) { run(); }
        for (int i = 0; i < n; i++) { work(i); }
        while (running) { tick(); }
        switch (mode) { case 1: break; }
        return;
    }
    public void simple() {
        value += 1;
    }
}
"""
        cls = JavaParser()._parse_file(src, "/fake/Demo.java", "/fake")
        assert cls is not None
        assert cls.method_complexities == [5, 1]
        assert len(cls.method_lines) == 2
        for m in cls.method_lines:
            assert m["end_line"] > m["start_line"]
            assert m["body_hash"]

    def test_avg_cyclomatic_complexity_is_decision_based(self):
        src = """
public class Demo {
    public void decisionHeavy() {
        if (x > 0) { run(); }
        for (int i = 0; i < n; i++) { work(i); }
        while (running) { tick(); }
        switch (mode) { case 1: break; }
        return;
    }
    public void simple() {
        value += 1;
    }
}
"""
        cls = JavaParser()._parse_file(src, "/fake/Demo.java", "/fake")
        ctx = AnalysisContext(job_id="j1", extracted_path="/fake")
        ctx.parsed_classes = [cls]
        ctx.project_metadata = {}
        result = CodeMetricsAnalyzer().analyze(ctx)
        assert result.metrics["avg_cyclomatic_complexity"] == 3.0
        assert result.metrics["avg_method_length"] > 0

    def test_duplication_detected_via_body_hash(self):
        src_a = """
public class ClassA {
    public void dup() {
        if (a) { return; }
        if (b) { return; }
        log.info("dup");
    }
}
"""
        src_b = src_a.replace("ClassA", "ClassB")
        cls_a = JavaParser()._parse_file(src_a, "/fake/ClassA.java", "/fake")
        cls_b = JavaParser()._parse_file(src_b, "/fake/ClassB.java", "/fake")
        assert cls_a.method_lines[0]["body_hash"] == cls_b.method_lines[0]["body_hash"]
        assert QualityMetricsAnalyzer()._estimate_duplication([cls_a, cls_b]) > 0.0

    def test_no_duplication_for_distinct_bodies(self):
        src = """
public class ClassA {
    public void one() {
        value += 1;
        step();
        log.debug("one");
    }
    public void two() {
        value += 2;
        jump();
        log.debug("two");
    }
}
"""
        cls = JavaParser()._parse_file(src, "/fake/ClassA.java", "/fake")
        assert len({m["body_hash"] for m in cls.method_lines}) == 2
        assert QualityMetricsAnalyzer()._estimate_duplication([cls]) == 0.0


# ─── #27 constructor regex scoped to class body ───

class TestStaticAnalyzerConstructorScope:
    def test_new_instantiation_not_misread_as_constructor(self):
        src = """
public class Foo {
    public void run() {
        Foo copy = new Foo(null);
    }
    private final Bar bar;
    public Foo(Bar bar) { this.bar = bar; }
}
"""
        parsed = _parse_java_classes(src, "/fake/Foo.java", "/fake")
        assert parsed
        foo = parsed[0][0]
        assert "Bar" in foo.injected_fields
        assert "null" not in foo.injected_fields
        assert "Bar" in foo.dependencies


# ─── #4 boundary_rules module must import cleanly ───

class TestBoundaryRulesImport:
    def test_boundary_rules_module_imports(self):
        assert issubclass(SingleOwnershipRule, BoundaryRule)


# ─── #8 checkpoint saved before pause/cancel return ───

class TestWorkerCheckpointOrdering:
    def test_worker_saves_checkpoint_before_pause_return(self):
        import app.services.workers.analysis_worker as worker

        state = MagicMock()
        state.status = "paused"
        state.stages = {}
        state.errors = []
        state.to_dict.return_value = {"status": "paused"}
        pipeline = MagicMock()
        pipeline.stage_names = ["extraction"]
        pipeline.execute.return_value = state
        job = MagicMock()
        job.status = "paused"

        with patch.object(worker, "_build_pipeline", return_value=pipeline), \
                patch.object(worker, "CheckpointManager") as MockCP, \
                patch.object(worker, "JobRepository") as MockJobRepo, \
                patch.object(worker, "ArtifactRepository"), \
                patch.object(worker, "events"), \
                patch.object(worker, "notifications"):
            MockJobRepo.return_value.get_job.return_value = job
            result = worker.handle_analysis_job("job-1")
            MockCP.return_value.save.assert_called_once_with("job-1", state)
            assert result["status"] == "paused"


# ─── #18 executor error entries use consistent schema ───

class TestExecutorErrorSchema:
    def test_sequential_pause_error_has_timestamp(self):
        executor = SequentialExecutor([DummyStage("A"), DummyStage("B")])
        state = executor.execute("job-p1", status_check_fn=lambda: "paused")
        assert state.errors
        err = state.errors[0]
        assert set(err.keys()) == {"stage", "error", "timestamp"}
        assert "paused" in err["error"]
        assert not state.has_completed("A")

    def test_parallel_failure_error_has_timestamp(self):
        executor = ParallelExecutor([FailingStage("F")])
        state = executor.execute("job-p2")
        assert state.errors
        for err in state.errors:
            assert set(err.keys()) == {"stage", "error", "timestamp"}
        assert any("boom" in e["error"] for e in state.errors)
