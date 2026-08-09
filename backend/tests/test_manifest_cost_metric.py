"""P8.5 — manifest reports real per-job AI usage from the cost tracker."""

from __future__ import annotations

import pytest


def _run_manifest(job_id: str) -> dict:
    from app.artifacts.models import Artifact, ArtifactMetadata
    from app.pipeline.context import PipelineContext
    from app.pipeline.stages.manifest import ManifestStage

    ctx = PipelineContext(job_id=job_id)
    ctx.state.job_id = job_id
    ctx.state.mark_started("static_analysis")
    ctx.state.mark_completed("static_analysis")
    ctx.set_result(
        "static_analysis",
        Artifact(
            metadata=ArtifactMetadata(artifact_type="static_analysis"),
            content={"classes": []},
        ),
    )
    return ManifestStage().execute(ctx).content


def _record_usage(job_id: str) -> None:
    from app.ai.service import get_ai_engine

    tracker = get_ai_engine().provider_registry.cost_tracker
    tracker.record_usage(
        "amazon.nova-pro-v1:0",
        input_tokens=1000,
        output_tokens=500,
        job_id=job_id,
        operation="test",
    )


class TestManifestCostMetric:
    def test_manifest_reports_real_cost_tracker_usage(self):
        job_id = "job-cost-metric-001"
        _record_usage(job_id)
        content = _run_manifest(job_id)
        summary = content["ai_summary"]
        assert summary["total_tokens_used"] == 1500
        assert summary["total_cost_estimate"] == pytest.approx(0.0016, rel=1e-6)
        assert summary["deterministic_fallbacks"] == 0
        assert summary["degraded_stages"] == []

    def test_manifest_with_no_ai_usage_reports_zero(self):
        content = _run_manifest("job-cost-metric-002")
        summary = content["ai_summary"]
        assert summary["total_tokens_used"] == 0
        assert summary["total_cost_estimate"] == 0.0
        assert summary["deterministic_fallbacks"] == 0

    def test_manifest_reports_degraded_stages(self):
        job_id = "job-cost-metric-003"
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.pipeline.context import PipelineContext
        from app.pipeline.stages.manifest import ManifestStage

        ctx = PipelineContext(job_id=job_id)
        ctx.state.job_id = job_id
        ctx.state.mark_started("ai_boundaries")
        ctx.state.mark_completed("ai_boundaries")
        ctx.state.stages["ai_boundaries"].is_degraded = True
        ctx.set_result(
            "ai_boundaries",
            Artifact(
                metadata=ArtifactMetadata(artifact_type="ai_boundaries", is_degraded=True),
                content={"services": []},
            ),
        )
        content = ManifestStage().execute(ctx).content
        summary = content["ai_summary"]
        assert summary["deterministic_fallbacks"] == 1
        assert summary["degraded_stages"] == ["ai_boundaries"]
