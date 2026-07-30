"""AI explainability stage — wraps Sprint 3 explainability generation."""

from __future__ import annotations

import structlog

from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import BaseAIStage

logger = structlog.get_logger(__name__)

DEFAULT_EXPLAINABILITY = {
    "recommendations": [], "business_capabilities": [], "risk_heatmap": [],
}


class AIExplainabilityStage(BaseAIStage):
    """Generates explainability data using Sprint 3 AI layer."""

    name = "ai_explainability"
    phase = "explainability"
    generator = "sprint3-ai-layer"
    requires_ai = True
    depends_on: list[str] = ["static_analysis", "enterprise_analysis", "ai_boundaries", "ai_readiness"]

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
        enterprise = context.get_result_data("enterprise_analysis")
        if enterprise:
            analysis_data["sprint2_analysis"] = enterprise
        services = context.get_result_data("ai_boundaries").get("services", [])
        readiness = context.get_result_data("ai_readiness")
        result = ai_orchestrator.generate_explainability(services, readiness, analysis_data)
        return result, "sprint3-deterministic"

    def fallback(self) -> dict:
        return DEFAULT_EXPLAINABILITY
