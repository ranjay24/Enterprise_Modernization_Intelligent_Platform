"""AI migration stage — wraps Sprint 3 migration planning."""

from __future__ import annotations

import structlog

from app.pipeline.context import PipelineContext
from app.pipeline.stages.base import BaseAIStage

logger = structlog.get_logger(__name__)


class AIMigrationStage(BaseAIStage):
    """Generates migration wave plan using Sprint 3 AI layer."""

    name = "ai_migration"
    phase = "migration_planning"
    generator = "sprint3-ai-layer"
    requires_ai = True
    depends_on: list[str] = ["ai_boundaries", "ai_readiness"]

    def prerequisites(self, context: PipelineContext) -> list[str]:
        missing = []
        if not context.get_result_data("ai_boundaries"):
            missing.append("ai_boundaries stage must complete first")
        if not context.get_result_data("ai_readiness"):
            missing.append("ai_readiness stage must complete first")
        return missing

    def execute_ai(self, context: PipelineContext) -> tuple[dict, str]:
        from app.ai import orchestrator as ai_orchestrator
        services = context.get_result_data("ai_boundaries").get("services", [])
        readiness = context.get_result_data("ai_readiness")
        result = ai_orchestrator.generate_migration_waves(services, readiness)
        return result, "sprint3-deterministic"

    def fallback(self) -> dict:
        return {"waves": [], "total_weeks": 0, "recommended_order": []}
