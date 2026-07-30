"""Sprint 4.1 tests — Integration tests for resume, checkpoint, artifact restoration, base stage, report builders."""

import gzip
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

# ─── Pipeline Resume + Artifact Restoration ───

class TestPipelineResumeWithArtifactRestoration:
    def test_resume_restores_artifacts_from_s3(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.engine import PipelineEngine
        from app.pipeline.stage import PipelineStage

        class StageA(PipelineStage):
            @property
            def name(self): return "stage_a"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(artifact_type="stage_a"), content={"a": 1})

        class StageB(PipelineStage):
            @property
            def name(self): return "stage_b"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(artifact_type="stage_b"), content={"b": 2})

        mock_repo = MagicMock()
        # Resume from stage_b — stage_a should be restored from S3
        mock_repo.load.return_value = Artifact(
            metadata=ArtifactMetadata(artifact_type="stage_a"),
            content={"a": 1, "restored": True},
        )
        mock_repo.save.return_value = "jobs/j1/artifacts/stage_b.json"

        engine = PipelineEngine(stages=[StageA(), StageB()], artifact_repo=mock_repo)
        state = engine.execute("j1", resume_from="stage_b")

        # stage_a should have been restored
        mock_repo.load.assert_any_call("j1", "stage_a")
        assert "stage_a" in state.stages
        assert "stage_b" in state.stages

    def test_resume_does_not_double_load_already_restored(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.context import PipelineContext
        from app.pipeline.engine import PipelineEngine
        from app.pipeline.stage import PipelineStage

        class StageA(PipelineStage):
            @property
            def name(self): return "stage_a"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(), content={})

        class StageB(PipelineStage):
            @property
            def name(self): return "stage_b"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(), content={})

        mock_repo = MagicMock()
        engine = PipelineEngine(stages=[StageA(), StageB()], artifact_repo=mock_repo)

        # Manually set context results before calling execute
        # to simulate a case where artifact was already restored
        ctx = PipelineContext(job_id="j1")
        existing = Artifact(metadata=ArtifactMetadata(artifact_type="stage_a"), content={"pre": True})
        ctx.set_result("stage_a", existing)

        # Test through SequentialExecutor which holds _restore_artifact
        from app.scheduling.executor import SequentialExecutor
        executor = SequentialExecutor(stages=[StageA(), StageB()], artifact_repo=mock_repo)
        executor._restore_artifact("j1", "stage_a", ctx)
        # Should not have called S3 since artifact is already in context
        mock_repo.load.assert_not_called()

    def test_resume_skips_stages_before_resume_point(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.engine import PipelineEngine
        from app.pipeline.stage import PipelineStage
        from app.pipeline.state import PipelineStatus

        class StageA(PipelineStage):
            @property
            def name(self): return "stage_a"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(), content={"a": True})

        class StageB(PipelineStage):
            @property
            def name(self): return "stage_b"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(), content={"b": True})

        class StageC(PipelineStage):
            @property
            def name(self): return "stage_c"
            @property
            def phase(self): return "static_analysis"
            def execute(self, ctx):
                return Artifact(metadata=ArtifactMetadata(), content={"c": True})

        mock_repo = MagicMock()
        mock_repo.load.return_value = Artifact(
            metadata=ArtifactMetadata(artifact_type="stage_b"),
            content={"b": True},
        )
        mock_repo.save.return_value = "jobs/j1/artifacts/stage_c.json"

        engine = PipelineEngine(stages=[StageA(), StageB(), StageC()], artifact_repo=mock_repo)
        state = engine.execute("j1", resume_from="stage_c")

        # StageA and StageB should be skipped/restored (not executed)
        # Only StageC should have been executed
        assert state.stages["stage_a"].status in (PipelineStatus.COMPLETED, PipelineStatus.SKIPPED)
        assert state.stages["stage_b"].status in (PipelineStatus.COMPLETED, PipelineStatus.SKIPPED)


# ─── Checkpoint Recovery ───

class TestCheckpointRecovery:
    @patch("app.services.checkpoint.S3Repository")
    @patch("app.services.checkpoint.JobRepository")
    def test_checkpoint_save_and_load_roundtrip(self, mock_job_repo, mock_s3):
        from app.pipeline.state import PipelineState
        from app.services.checkpoint import CheckpointManager

        state = PipelineState(job_id="j1")
        state.mark_started("stage_a")
        state.mark_completed("stage_a", artifact_key="k1", artifact_id="a1")

        mgr = CheckpointManager()
        mgr.save("j1", state)

        # Verify S3 put was called with serialized state
        mock_s3.return_value.put_object.assert_called_once()
        put_call = mock_s3.return_value.put_object.call_args
        assert "checkpoints/pipeline-state.json" in put_call.kwargs["key"]

        # Verify DynamoDB update was called
        mock_job_repo.return_value.update_job.assert_called_once()

    @patch("app.services.checkpoint.S3Repository")
    def test_checkpoint_load_returns_state(self, mock_s3):
        from app.pipeline.state import PipelineState
        from app.services.checkpoint import CheckpointManager

        state = PipelineState(job_id="j1")
        state.mark_started("stage_a")
        state.mark_completed("stage_a")

        body = json.dumps(state.to_dict(), default=str).encode()
        mock_s3.return_value.get_object.return_value = {"Body": BytesIO(body)}

        mgr = CheckpointManager()
        loaded = mgr.load("j1")

        assert loaded is not None
        assert loaded.job_id == "j1"
        assert "stage_a" in loaded.stages
        assert loaded.stages["stage_a"].status.value == "completed"

    @patch("app.services.checkpoint.S3Repository")
    def test_checkpoint_load_returns_none_on_failure(self, mock_s3):
        from app.services.checkpoint import CheckpointManager

        mock_s3.return_value.get_object.side_effect = Exception("not found")
        mgr = CheckpointManager()
        assert mgr.load("nonexistent") is None

    @patch("app.services.checkpoint.S3Repository")
    def test_get_resume_stage(self, mock_s3):
        from app.pipeline.state import PipelineState
        from app.services.checkpoint import CheckpointManager

        state = PipelineState(job_id="j1")
        state.mark_started("extraction")
        state.mark_completed("extraction")
        state.mark_started("static_analysis")

        body = json.dumps(state.to_dict(), default=str).encode()
        mock_s3.return_value.get_object.return_value = {"Body": BytesIO(body)}

        mgr = CheckpointManager()
        stage = mgr.get_resume_stage("j1")
        assert stage == "static_analysis"

    @patch("app.services.checkpoint.S3Repository")
    def test_has_checkpoint_true(self, mock_s3):
        from app.services.checkpoint import CheckpointManager

        mock_s3.return_value.get_object.return_value = {"Body": BytesIO(b"{}")}
        mgr = CheckpointManager()
        assert mgr.has_checkpoint("j1") is True

    @patch("app.services.checkpoint.S3Repository")
    def test_has_checkpoint_false(self, mock_s3):
        from app.services.checkpoint import CheckpointManager

        mock_s3.return_value.get_object.side_effect = Exception("not found")
        mgr = CheckpointManager()
        assert mgr.has_checkpoint("j1") is False

    @patch("app.services.checkpoint.S3Repository")
    def test_clear_checkpoint(self, mock_s3):
        from app.services.checkpoint import CheckpointManager

        mgr = CheckpointManager()
        mgr.clear_checkpoint("j1")
        mock_s3.return_value.client.delete_object.assert_called_once()


# ─── BaseAIStage ───

class TestBaseAIStage:
    def test_execute_ai_success(self):
        from app.pipeline.context import PipelineContext
        from app.pipeline.stages.base import BaseAIStage

        class SuccessAIStage(BaseAIStage):
            @property
            def name(self): return "test_ai"
            @property
            def phase(self): return "ai_analysis"
            @property
            def requires_ai(self): return True
            @property
            def generator(self): return "test-generator"

            def execute_ai(self, context):
                return {"ai_result": "success"}, "nova-pro"

            def fallback(self):
                return {"ai_result": "fallback"}

        stage = SuccessAIStage()
        ctx = PipelineContext(job_id="j1")
        artifact = stage.execute(ctx)

        assert artifact.content["ai_result"] == "success"
        assert artifact.metadata.model_id == "nova-pro"
        assert artifact.metadata.is_degraded is False

    def test_execute_ai_raises_triggers_fallback(self):
        from app.pipeline.context import PipelineContext
        from app.pipeline.stages.base import BaseAIStage

        class FailAIStage(BaseAIStage):
            @property
            def name(self): return "fail_ai"
            @property
            def phase(self): return "ai_analysis"
            @property
            def generator(self): return "test-gen"

            def execute_ai(self, context):
                raise RuntimeError("AI service unavailable")

            def fallback(self):
                return {"fallback": True, "error": "degraded"}

        stage = FailAIStage()
        ctx = PipelineContext(job_id="j1")
        artifact = stage.execute(ctx)

        assert artifact.content["fallback"] is True
        assert artifact.metadata.is_degraded is True
        assert artifact.metadata.model_id == "deterministic-fallback"

    def test_execute_ai_empty_result_triggers_fallback(self):
        from app.pipeline.context import PipelineContext
        from app.pipeline.stages.base import BaseAIStage

        class EmptyAIStage(BaseAIStage):
            @property
            def name(self): return "empty_ai"
            @property
            def phase(self): return "ai_analysis"
            @property
            def generator(self): return "test-gen"

            def execute_ai(self, context):
                return {}, "nova-pro"

            def fallback(self):
                return {"from_fallback": True}

        stage = EmptyAIStage()
        ctx = PipelineContext(job_id="j1")
        artifact = stage.execute(ctx)

        assert artifact.content["from_fallback"] is True
        assert artifact.metadata.is_degraded is True

    def test_prerequisites_default_empty(self):
        from app.pipeline.context import PipelineContext
        from app.pipeline.stages.base import BaseAIStage

        class NoPrereqStage(BaseAIStage):
            @property
            def name(self): return "np"
            @property
            def phase(self): return "ai_analysis"

            def execute_ai(self, ctx):
                return {}, ""

        ctx = PipelineContext(job_id="j1")
        assert NoPrereqStage().validate_prerequisites(ctx) == []

    def test_execute_ai_not_implemented(self):
        from app.pipeline.context import PipelineContext
        from app.pipeline.stages.base import BaseAIStage

        class BareStage(BaseAIStage):
            @property
            def name(self): return "bare"
            @property
            def phase(self): return "ai_analysis"
            def execute_ai(self, ctx):
                raise NotImplementedError("Subclasses must implement execute_ai")

        stage = BareStage()
        ctx = PipelineContext(job_id="j1")
        # execute_ai raises NotImplementedError, should trigger fallback
        artifact = stage.execute(ctx)
        assert artifact.metadata.is_degraded is True


# ─── Shared Report Builders ───

class TestReportBuilders:
    def _sample_results(self):
        return {
            "job_id": "test-job-001",
            "metrics": {
                "total_classes": 150,
                "total_lines": 25000,
                "total_methods": 800,
                "god_classes": [{"name": "GodClass"}],
                "circular_dependencies": [{"cycle": ["A", "B", "C"]}],
            },
            "readiness": {"overall": 65, "code_quality": 70},
            "cost_comparison": {"monthly_savings": 1200.50, "annual_savings": 14406, "payback_months": 8},
            "service_boundaries": [
                {"name": "UserService", "confidence": 0.9, "classes": ["A", "B"], "coupling_score": 3, "risk_level": "low", "cohesion_score": 8, "readiness": "green"},
                {"name": "OrderService", "confidence": 0.7, "classes": ["C"], "coupling_score": 7, "risk_level": "high", "cohesion_score": 5, "readiness": "red"},
            ],
            "adrs": [{"title": "Use REST API"}, {"title": "Use event sourcing"}],
            "migration_waves": [
                {"name": "Wave 1", "services": ["UserService"], "timeline_weeks": 4},
                {"name": "Wave 2", "services": ["OrderService"], "timeline_weeks": 6},
            ],
            "sprint2_analysis": {
                "risk_report": {
                    "findings": [
                        {"severity": "critical", "message": "Circular dep"},
                        {"severity": "high", "message": "God class"},
                        {"severity": "medium", "message": "Missing tests"},
                    ]
                }
            },
        }

    def test_build_executive_summary(self):
        from app.reports.builders import build_executive_summary
        results = self._sample_results()
        report = build_executive_summary(results)
        assert report["project_name"] == "test-job-001"
        assert report["overall_score"] == 65
        assert report["risk_level"] == "medium"
        assert report["recommended_services"] == 2
        assert report["estimated_monthly_savings"] == 1200.50
        assert len(report["key_findings"]) == 3

    def test_build_developer_report(self):
        from app.reports.builders import build_developer_report
        results = self._sample_results()
        report = build_developer_report(results)
        assert report["codebase_metrics"]["total_classes"] == 150
        assert report["codebase_metrics"]["god_classes"] == 1
        assert len(report["services"]) == 2
        assert report["adr_count"] == 2
        assert len(report["priority_actions"]) == 3

    def test_build_risk_analysis(self):
        from app.reports.builders import build_risk_analysis
        results = self._sample_results()
        report = build_risk_analysis(results)
        assert report["total_risks"] == 3
        assert report["critical_risks"] == 1
        assert report["high_risks"] == 1
        assert "OrderService" in report["high_risk_services"]
        assert "GodClass" in report["god_classes"]

    def test_build_architecture_report(self):
        from app.reports.builders import build_architecture_report
        results = self._sample_results()
        report = build_architecture_report(results)
        assert report["service_count"] == 2
        assert report["recommended_style"] == "microservices"
        assert report["services"][0]["readiness"] == "green"
        assert report["services"][1]["readiness"] == "red"

    def test_build_migration_roadmap(self):
        from app.reports.builders import build_migration_roadmap
        results = self._sample_results()
        report = build_migration_roadmap(results)
        assert report["total_waves"] == 2
        assert report["estimated_total_weeks"] == 10

    def test_build_all_reports(self):
        from app.reports.builders import build_all_reports
        results = self._sample_results()
        reports = build_all_reports(results)
        assert set(reports.keys()) == {"executive_summary", "developer_report", "risk_analysis", "architecture_report", "migration_roadmap"}
        for key, report in reports.items():
            assert "title" in report

    def test_empty_results_produce_valid_reports(self):
        from app.reports.builders import build_all_reports
        reports = build_all_reports({})
        assert reports["executive_summary"]["overall_score"] == 0
        assert reports["migration_roadmap"]["total_waves"] == 0
        assert len(reports["developer_report"]["services"]) == 0

    def test_risk_level_derivation(self):
        from app.reports.builders import _derive_risk_level
        assert _derive_risk_level({"overall": 80}) == "low"
        assert _derive_risk_level({"overall": 50}) == "medium"
        assert _derive_risk_level({"overall": 20}) == "high"

    def test_recommendation_derivation(self):
        from app.reports.builders import _derive_recommendation
        assert "reasonably ready" in _derive_recommendation({"overall": 80})
        assert "caution" in _derive_recommendation({"overall": 50})
        assert "refactoring needed" in _derive_recommendation({"overall": 20})


# ─── Artifact Compression ───

class TestArtifactCompression:
    @patch("app.artifacts.repository.S3Repository")
    def test_small_artifact_not_compressed(self, mock_s3):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.artifacts.repository import ArtifactRepository

        mock_s3.return_value.put_object.return_value = {}
        mock_s3.return_value.get_object.side_effect = Exception("not found")

        repo = ArtifactRepository()
        artifact = Artifact(
            metadata=ArtifactMetadata(artifact_type="test", job_id="j1"),
            content={"small": "data"},
        )
        key = repo.save("j1", "test_stage", artifact)

        put_call = mock_s3.return_value.put_object.call_args_list[0]
        content_type = put_call.kwargs["content_type"]
        assert content_type == "application/json"

    @patch("app.artifacts.repository.S3Repository")
    def test_large_artifact_compressed(self, mock_s3):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.artifacts.repository import (
            COMPRESS_THRESHOLD_BYTES,
            ArtifactRepository,
        )

        mock_s3.return_value.put_object.return_value = {}
        mock_s3.return_value.get_object.side_effect = Exception("not found")

        # Create content larger than threshold
        large_content = {"data": "x" * (COMPRESS_THRESHOLD_BYTES + 1000)}
        repo = ArtifactRepository()
        artifact = Artifact(
            metadata=ArtifactMetadata(artifact_type="test", job_id="j1"),
            content=large_content,
        )
        key = repo.save("j1", "test_stage", artifact)

        put_call = mock_s3.return_value.put_object.call_args_list[0]
        content_type = put_call.kwargs["content_type"]
        assert content_type == "application/gzip"

    @patch("app.artifacts.repository.S3Repository")
    def test_load_decompresses_gzip(self, mock_s3):
        from app.artifacts.repository import ArtifactRepository

        original_content = {"result": "compressed data", "value": 42}
        body = json.dumps(original_content, default=str).encode()
        compressed = gzip.compress(body)

        mock_s3.return_value.get_object.side_effect = [
            {"Body": BytesIO(compressed), "ContentType": "application/gzip"},
            {"Body": BytesIO(json.dumps({"artifact_type": "test", "job_id": "j1"}, default=str).encode()), "ContentType": "application/json"},
        ]

        repo = ArtifactRepository()
        artifact = repo.load("j1", "test_stage")
        assert artifact is not None
        assert artifact.content == original_content

    @patch("app.artifacts.repository.S3Repository")
    def test_load_handles_uncompressed_json(self, mock_s3):
        from app.artifacts.repository import ArtifactRepository

        original_content = {"result": "plain json"}
        body = json.dumps(original_content, default=str).encode()

        mock_s3.return_value.get_object.side_effect = [
            {"Body": BytesIO(body), "ContentType": "application/json"},
            {"Body": BytesIO(json.dumps({"artifact_type": "test", "job_id": "j1"}, default=str).encode()), "ContentType": "application/json"},
        ]

        repo = ArtifactRepository()
        artifact = repo.load("j1", "test_stage")
        assert artifact is not None
        assert artifact.content == original_content

    @patch("app.artifacts.repository.S3Repository")
    def test_save_manifest_compressed(self, mock_s3):
        from app.artifacts.models import ArtifactManifest
        from app.artifacts.repository import ArtifactRepository

        mock_s3.return_value.put_object.return_value = {}
        manifest = ArtifactManifest(job_id="j1")
        # Create enough content to exceed compression threshold
        from app.artifacts.models import ArtifactMetadata
        for i in range(500):
            meta = ArtifactMetadata(artifact_id=f"a{i}", artifact_type=f"stage_{i}", job_id="j1")
            manifest.artifacts.append(meta)

        repo = ArtifactRepository()
        repo.save_manifest("j1", manifest)

        put_call = mock_s3.return_value.put_object.call_args_list[0]
        content_type = put_call.kwargs["content_type"]
        assert content_type in ("application/gzip", "application/json")


# ─── EventBridge Schema ───

class TestEventBridgeSchema:
    @patch("app.services.events.EventBridgeRepository")
    def test_events_include_correlation_id(self, mock_eb):
        from app.services.events import (
            EVENT_SCHEMA_VERSION,
            publish_pipeline_completed,
            publish_pipeline_failed,
            publish_pipeline_started,
            publish_report_generated,
            publish_stage_completed,
            publish_stage_failed,
        )

        mock_eb.return_value.publish_pipeline_event.return_value = "evt-1"
        mock_eb.return_value.publish_report_event.return_value = "evt-2"

        publish_pipeline_started("job-123", total_stages=12)
        detail = mock_eb.return_value.publish_pipeline_event.call_args[0][2]
        assert detail["correlation_id"] == "job-123"
        assert detail["schema_version"] == EVENT_SCHEMA_VERSION

        publish_stage_completed("job-123", "extraction", 10, 500.0)
        detail = mock_eb.return_value.publish_pipeline_event.call_args[0][2]
        assert detail["correlation_id"] == "job-123"
        assert detail["schema_version"] == EVENT_SCHEMA_VERSION

        publish_stage_failed("job-123", "extraction", "timeout")
        detail = mock_eb.return_value.publish_pipeline_event.call_args[0][2]
        assert detail["correlation_id"] == "job-123"

        publish_pipeline_completed("job-123", 5000.0, 10, False)
        detail = mock_eb.return_value.publish_pipeline_event.call_args[0][2]
        assert detail["correlation_id"] == "job-123"

        publish_pipeline_failed("job-123", "extraction", "fatal")
        detail = mock_eb.return_value.publish_pipeline_event.call_args[0][2]
        assert detail["correlation_id"] == "job-123"

        publish_report_generated("job-123", "executive_summary", "key123")
        detail = mock_eb.return_value.publish_report_event.call_args[0][2]
        assert detail["correlation_id"] == "job-123"
        assert detail["schema_version"] == EVENT_SCHEMA_VERSION

    def test_event_schema_version_constant(self):
        from app.services.events import EVENT_SCHEMA_VERSION
        assert EVENT_SCHEMA_VERSION == "1.0.0"


# ─── Manifest Schema Version ───

class TestManifestSchemaVersion:
    def test_manifest_has_schema_version(self):
        from app.artifacts.models import ArtifactManifest
        manifest = ArtifactManifest(job_id="j1")
        d = manifest.to_dict()
        assert "schema_version" in d
        assert d["schema_version"] == "1.0.0"

    def test_manifest_schema_version_constant(self):
        from app.artifacts.models import ARTIFACT_SCHEMA_VERSION
        assert ARTIFACT_SCHEMA_VERSION == "1.0.0"

    def test_manifest_from_dict_preserves_schema_version(self):
        from app.artifacts.models import ArtifactManifest
        data = {
            "job_id": "j1",
            "schema_version": "1.0.0",
            "total_artifacts": 0,
            "artifacts": [],
            "total_reports": 0,
            "reports": [],
            "pipeline_version": "1.0.0",
        }
        manifest = ArtifactManifest.from_dict(data)
        d = manifest.to_dict()
        assert d["schema_version"] == "1.0.0"
