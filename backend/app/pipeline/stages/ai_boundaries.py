"""AI boundaries stage — wraps Sprint 3 service boundary detection."""

from __future__ import annotations

import structlog

from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import BaseAIStage

logger = structlog.get_logger(__name__)


class AIBoundariesStage(BaseAIStage):
    """Detects microservice boundaries using Sprint 3 AI layer."""

    name = "ai_boundaries"
    phase = "service_boundary"
    generator = "sprint3-ai-layer"
    requires_ai = True
    depends_on: list[str] = ["static_analysis", "enterprise_analysis"]

    def prerequisites(self, context: PipelineContext) -> list[str]:
        missing = []
        if not context.get_result_data("static_analysis"):
            missing.append("static_analysis stage must complete first")
        if not context.get_result_data("enterprise_analysis"):
            missing.append("enterprise_analysis stage must complete first")
        return missing

    def execute_ai(self, context: PipelineContext) -> tuple[dict, str]:
        from app.ai import orchestrator as ai_orchestrator
        analysis_data = context.get_result_data("static_analysis")
        # Merge enterprise_analysis data which contains candidate_services
        enterprise = context.get_result_data("enterprise_analysis")
        if enterprise:
            analysis_data["candidate_services"] = enterprise.get("candidate_services", [])
            analysis_data["bounded_contexts"] = enterprise.get("bounded_contexts", [])
            analysis_data["sprint2_analysis"] = enterprise
            analysis_data["quality_metrics"] = enterprise.get("quality_metrics", {})
            analysis_data["coupling_analysis"] = enterprise.get("coupling_analysis", {})
        result = ai_orchestrator.analyze_service_boundaries(analysis_data)
        model_id = result.pop("_model_id", "deterministic-fallback")
        return result, model_id

    def fallback(self) -> dict:
        return {"services": [], "summary": "Boundary detection unavailable"}
