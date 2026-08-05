"""AI ADR stage — wraps Sprint 3 ADR generation."""

from __future__ import annotations

import structlog

from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import BaseAIStage

logger = structlog.get_logger(__name__)


class AIADRStage(BaseAIStage):
    """Generates Architecture Decision Records using Sprint 3 AI layer."""

    name = "ai_adrs"
    phase = "adr_generation"
    generator = "sprint3-ai-layer"
    requires_ai = True
    depends_on: list[str] = ["static_analysis", "enterprise_analysis", "ai_boundaries"]

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
        result = ai_orchestrator.generate_adrs(analysis_data, services)
        model_id = result.pop("_model_id", "deterministic-fallback")
        return result, model_id

    def fallback(self) -> dict:
        return {"adrs": []}
