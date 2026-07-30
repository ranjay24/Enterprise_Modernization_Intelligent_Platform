"""AI readiness stage — wraps Sprint 3 readiness scoring."""

from __future__ import annotations

import structlog

from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import BaseAIStage

logger = structlog.get_logger(__name__)

DEFAULT_READINESS = {
    "code_quality": {"score": 50, "evidence": "Analysis incomplete"},
    "architecture": {"score": 50, "evidence": "Analysis incomplete"},
    "cloud_readiness": {"score": 50, "evidence": "Analysis incomplete"},
    "service_separation": {"score": 50, "evidence": "Analysis incomplete"},
    "database_coupling": {"score": 50, "evidence": "Analysis incomplete"},
    "documentation": {"score": 30, "evidence": "Limited documentation detected"},
    "overall": 50,
    "confidence": 0.6,
    "summary": "Analysis incomplete — using defaults",
}


class AIReadinessStage(BaseAIStage):
    """Generates readiness scores using Sprint 3 AI layer."""

    name = "ai_readiness"
    phase = "readiness_scoring"
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
        # Merge enterprise_analysis for sprint2 readiness scores
        enterprise = context.get_result_data("enterprise_analysis")
        if enterprise:
            analysis_data["sprint2_analysis"] = enterprise
        result = ai_orchestrator.generate_readiness_scores(analysis_data)
        if not result or result.get("overall", 0) == 0:
            return DEFAULT_READINESS, "sprint3-deterministic-empty"
        return result, "sprint3-deterministic"

    def fallback(self) -> dict:
        return DEFAULT_READINESS
