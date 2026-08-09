"""AI cost stage — wraps Sprint 3 cost analysis."""

from __future__ import annotations

import structlog

from app.core.settings import get_settings
from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import BaseAIStage

logger = structlog.get_logger(__name__)

DEFAULT_COST = {
    "current_monthly": 0, "post_migration_monthly": 0,
    "monthly_savings": 0, "annual_savings": 0,
    "one_time_cost": 0, "payback_months": 24,
    "breakdown_current": {}, "breakdown_post": {},
}


class AICostStage(BaseAIStage):
    """Generates cost comparison using Sprint 3 AI layer."""

    name = "ai_cost"
    phase = "cost_analysis"
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

        # Live AWS on-demand rates are opt-in; any lookup failure falls back to
        # the fixed formulas inside generate_cost_comparison, so this stage
        # stays deterministic and offline-safe by default.
        pricing = None
        settings = get_settings()
        if settings.aws_pricing_enabled:
            from app.services.pricing_service import AwsPricingService

            pricing = AwsPricingService(
                region=settings.aws_region,
                cache_ttl=settings.aws_pricing_cache_ttl,
            )
        result = ai_orchestrator.generate_cost_comparison(analysis_data, services, pricing=pricing)
        return result, "sprint3-deterministic"

    def fallback(self) -> dict:
        return DEFAULT_COST
