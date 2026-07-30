"""AI Service — high-level AI service interface for the application."""

from __future__ import annotations

from typing import Any

import structlog

from app.ai.contracts.adr import AIDecisionRecord
from app.ai.contracts.developer import AIDeveloperReport
from app.ai.contracts.executive import AIExecutiveSummary
from app.ai.contracts.migration import AIMigrationPlan
from app.ai.contracts.recommendation import AIRecommendation
from app.ai.engine import AIEngine

logger = structlog.get_logger(__name__)

_engine: AIEngine | None = None


def get_ai_engine() -> AIEngine:
    """Get or create the singleton AI engine."""
    global _engine
    if _engine is None:
        _engine = AIEngine()
    return _engine


class AIService:
    """High-level AI service providing modernization intelligence.

    Each method represents a distinct AI analysis capability.
    All methods support AI + deterministic fallback.
    """

    def __init__(self, engine: AIEngine | None = None):
        self._engine = engine or get_ai_engine()

    @property
    def engine(self) -> AIEngine:
        return self._engine

    def generate_recommendations(
        self, analysis_data: dict, job_id: str = ""
    ) -> tuple[list[AIRecommendation], dict]:
        """Generate AI-powered modernization recommendations."""
        ctx = self._engine.build_context(analysis_data, job_id)
        template_vars = ctx.to_template_variables()
        template_vars["candidate_services_json"] = _compact_json(ctx.candidate_services)
        template_vars["bounded_contexts_json"] = _compact_json(ctx.bounded_contexts)
        template_vars["risk_findings_json"] = _compact_json(ctx.risk_findings)

        result, metadata, used_ai = self._engine.invoke_ai_with_fallback(
            prompt_id="recommendations/service_recommendations",
            template_variables=template_vars,
            fallback_fn=lambda: self._engine._recommendation_engine.generate_deterministic(ctx),
            expected_fields=["recommendations"],
            job_id=job_id,
        )

        if used_ai and isinstance(result, dict):
            recommendations = self._engine._recommendation_engine.generate(ctx, result)
        elif isinstance(result, list):
            recommendations = result
        else:
            recommendations = self._engine._recommendation_engine.generate_deterministic(ctx)

        return recommendations, metadata

    def generate_adrs(
        self, analysis_data: dict, job_id: str = ""
    ) -> tuple[list[AIDecisionRecord], dict]:
        """Generate Architecture Decision Records."""
        ctx = self._engine.build_context(analysis_data, job_id)
        template_vars = ctx.to_template_variables()
        template_vars["service_boundaries_json"] = _compact_json(ctx.candidate_services)
        template_vars["risk_findings_json"] = _compact_json(ctx.risk_findings)

        result, metadata, used_ai = self._engine.invoke_ai_with_fallback(
            prompt_id="adr/adr_generation",
            template_variables=template_vars,
            fallback_fn=lambda: self._engine._adr_generator.generate_deterministic(ctx),
            expected_fields=["adrs"],
            job_id=job_id,
        )

        if used_ai and isinstance(result, dict):
            adrs = self._engine._adr_generator.generate(ctx, result)
        elif isinstance(result, list):
            adrs = result
        else:
            adrs = self._engine._adr_generator.generate_deterministic(ctx)

        return adrs, metadata

    def generate_migration_plan(
        self, analysis_data: dict, job_id: str = ""
    ) -> tuple[AIMigrationPlan, dict]:
        """Generate phased migration plan."""
        ctx = self._engine.build_context(analysis_data, job_id)
        template_vars = ctx.to_template_variables()
        template_vars["service_boundaries_json"] = _compact_json(ctx.candidate_services)
        template_vars["readiness_scores_json"] = _compact_json(ctx.readiness_summary)
        template_vars["service_deps_json"] = _compact_json({})

        result, metadata, used_ai = self._engine.invoke_ai_with_fallback(
            prompt_id="migration/migration_plan",
            template_variables=template_vars,
            fallback_fn=lambda: self._engine._migration_planner.generate_deterministic(ctx),
            expected_fields=["waves"],
            job_id=job_id,
        )

        if used_ai and isinstance(result, dict):
            plan = self._engine._migration_planner.generate(ctx, result)
        else:
            plan = self._engine._migration_planner.generate_deterministic(ctx)

        return plan, metadata

    def generate_executive_summary(
        self, analysis_data: dict, job_id: str = ""
    ) -> tuple[AIExecutiveSummary, dict]:
        """Generate executive summary."""
        ctx = self._engine.build_context(analysis_data, job_id)
        template_vars = ctx.to_template_variables()

        result, metadata, used_ai = self._engine.invoke_ai_with_fallback(
            prompt_id="executive/executive_summary",
            template_variables=template_vars,
            fallback_fn=lambda: self._engine._executive_generator.generate_deterministic(ctx),
            expected_fields=["executive_summary"],
            job_id=job_id,
        )

        if used_ai and isinstance(result, dict):
            summary = self._engine._executive_generator.generate(ctx, result)
        else:
            summary = self._engine._executive_generator.generate_deterministic(ctx)

        return summary, metadata

    def generate_developer_report(
        self, analysis_data: dict, job_id: str = ""
    ) -> tuple[AIDeveloperReport, dict]:
        """Generate developer report."""
        ctx = self._engine.build_context(analysis_data, job_id)
        template_vars = ctx.to_template_variables()
        template_vars["metrics_json"] = _compact_json(ctx.metrics_summary)
        template_vars["quality_metrics_json"] = _compact_json(ctx.quality_summary)
        template_vars["risk_findings_json"] = _compact_json(ctx.risk_findings)
        template_vars["readiness_dimensions_json"] = _compact_json(ctx.readiness_summary)

        result, metadata, used_ai = self._engine.invoke_ai_with_fallback(
            prompt_id="developer/developer_report",
            template_variables=template_vars,
            fallback_fn=lambda: self._engine._developer_generator.generate_deterministic(ctx),
            expected_fields=["architecture_findings"],
            job_id=job_id,
        )

        if used_ai and isinstance(result, dict):
            report = self._engine._developer_generator.generate(ctx, result)
        else:
            report = self._engine._developer_generator.generate_deterministic(ctx)

        return report, metadata

    def discover_services(
        self, analysis_data: dict, job_id: str = ""
    ) -> tuple[dict, dict]:
        """Discover candidate microservices."""
        ctx = self._engine.build_context(analysis_data, job_id)
        discovery = self._engine._discovery.discover(ctx)
        return discovery, {"used_ai": False}

    def get_health(self) -> dict:
        """AI subsystem health check."""
        return self._engine.get_health()


def _compact_json(data: Any, max_chars: int | None = None) -> str:
    """Compact JSON for prompt embedding.

    Default max_chars comes from the active analysis profile.
    """
    if max_chars is None:
        from app.core.analysis_profile import get_active_profile
        from app.core.settings import get_settings
        _s = get_settings()
        max_chars = get_active_profile(_s.analysis_mode, _s.bedrock_max_tokens, _s.ai_prompt_max_tokens).compact_json_max_chars
    import json
    result = json.dumps(data, default=str, ensure_ascii=False)
    if len(result) > max_chars:
        return result[:max_chars] + '..."'
    return result
