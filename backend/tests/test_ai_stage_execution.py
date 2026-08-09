"""Stage-level tests for AI stages — honest model id reporting, fallback, degradation.

Covers P7.4: AIBoundariesStage and AIADRStage execute() with a stubbed
orchestrator layer, verifying that the _model_id returned by the orchestrator
is propagated into ArtifactMetadata, that is_degraded is set on failure or
empty results, and that fallback content is produced.
"""

from unittest.mock import patch

from app.artifacts.models import Artifact, ArtifactMetadata
from app.pipeline.context import PipelineContext
from app.pipeline.stages.ai_adrs import AIADRStage
from app.pipeline.stages.ai_boundaries import AIBoundariesStage


def _context(job_id: str = "j-stage-1") -> PipelineContext:
    ctx = PipelineContext(job_id=job_id)
    ctx.set_result(
        "static_analysis",
        Artifact(
            metadata=ArtifactMetadata(artifact_type="static_analysis"),
            content={"classes": [{"name": "OrderService", "package": "com.acme"}]},
        ),
    )
    ctx.set_result(
        "enterprise_analysis",
        Artifact(
            metadata=ArtifactMetadata(artifact_type="enterprise_analysis"),
            content={
                "candidate_services": [
                    {"name": "OrderService", "classes": ["OrderService"], "confidence": 0.8}
                ],
                "bounded_contexts": [],
            },
        ),
    )
    ctx.set_result(
        "ai_boundaries",
        Artifact(
            metadata=ArtifactMetadata(artifact_type="ai_boundaries"),
            content={"services": [{"name": "OrderService", "classes": ["OrderService"]}]},
        ),
    )
    return ctx


class TestAIBoundariesStage:
    def test_execute_ai_success_reports_real_model_id(self):
        def fake_analyze(analysis_data):
            return {
                "services": [{"name": "OrderService", "classes": ["OrderService"]}],
                "total_services": 1,
                "_model_id": "amazon.nova-pro-v1:0",
            }

        with patch("app.ai.orchestrator.analyze_service_boundaries", side_effect=fake_analyze):
            artifact = AIBoundariesStage().execute(_context())

        assert artifact.content["total_services"] == 1
        assert artifact.metadata.model_id == "amazon.nova-pro-v1:0"
        assert artifact.metadata.is_degraded is False
        assert artifact.metadata.generator == "sprint3-ai-layer"

    def test_execute_ai_omits_model_id_from_content(self):
        def fake_analyze(analysis_data):
            return {"services": [], "_model_id": "nova-pro"}

        with patch("app.ai.orchestrator.analyze_service_boundaries", side_effect=fake_analyze):
            artifact = AIBoundariesStage().execute(_context())

        assert "_model_id" not in artifact.content

    def test_execute_ai_fallback_on_exception(self):
        def fake_analyze(analysis_data):
            raise RuntimeError("bedrock throttled")

        with patch("app.ai.orchestrator.analyze_service_boundaries", side_effect=fake_analyze):
            artifact = AIBoundariesStage().execute(_context())

        assert artifact.content == {"services": [], "summary": "Boundary detection unavailable"}
        assert artifact.metadata.is_degraded is True
        assert artifact.metadata.model_id == "deterministic-fallback"

    def test_execute_ai_empty_result_triggers_fallback(self):
        def fake_analyze(analysis_data):
            return {"_model_id": "nova-lite"}

        with patch("app.ai.orchestrator.analyze_service_boundaries", side_effect=fake_analyze):
            artifact = AIBoundariesStage().execute(_context())

        assert artifact.metadata.is_degraded is True
        assert artifact.metadata.model_id == "nova-lite-empty"

    def test_prerequisites_require_static_and_enterprise_analysis(self):
        ctx = PipelineContext(job_id="j-prereq")
        missing = AIBoundariesStage().prerequisites(ctx)
        assert "static_analysis" in missing[0]
        assert "enterprise_analysis" in missing[1]


class TestAIADRStage:
    def test_execute_ai_success_reports_real_model_id(self):
        def fake_generate(analysis_data, services):
            return {
                "adrs": [{"id": "ADR-0001", "title": "Introduce Order Service"}],
                "_model_id": "amazon.nova-pro-v1:0",
            }

        with patch("app.ai.orchestrator.generate_adrs", side_effect=fake_generate):
            artifact = AIADRStage().execute(_context())

        assert artifact.content["adrs"][0]["id"] == "ADR-0001"
        assert artifact.metadata.model_id == "amazon.nova-pro-v1:0"
        assert artifact.metadata.is_degraded is False
        assert "_model_id" not in artifact.content

    def test_execute_ai_fallback_on_exception(self):
        def fake_generate(analysis_data, services):
            raise RuntimeError("bedrock throttled")

        with patch("app.ai.orchestrator.generate_adrs", side_effect=fake_generate):
            artifact = AIADRStage().execute(_context())

        assert artifact.content == {"adrs": []}
        assert artifact.metadata.is_degraded is True
        assert artifact.metadata.model_id == "deterministic-fallback"

    def test_execute_ai_empty_result_triggers_fallback(self):
        def fake_generate(analysis_data, services):
            return {"_model_id": "nova-lite"}

        with patch("app.ai.orchestrator.generate_adrs", side_effect=fake_generate):
            artifact = AIADRStage().execute(_context())

        assert artifact.content == {"adrs": []}
        assert artifact.metadata.is_degraded is True
        assert artifact.metadata.model_id == "nova-lite-empty"
