"""AI Executive Summary Generator — generates executive-friendly reports."""

from __future__ import annotations

import structlog

from app.ai.context.builder import AIContext
from app.ai.contracts.executive import (
    AIExecutiveSummary,
    BusinessRisk,
    CloudReadinessAssessment,
    CostImpact,
    ExecutiveRecommendation,
)
from app.core.analysis_profile import get_profile_for_settings

logger = structlog.get_logger(__name__)


class AIExecutiveSummaryGenerator:
    """Generates AI-powered executive summaries."""

    def generate(self, ai_context: AIContext, parsed_response: dict) -> AIExecutiveSummary:
        """Generate executive summary from parsed AI response."""
        cost_impact = None
        if parsed_response.get("cost_impact"):
            cost_data = parsed_response["cost_impact"]
            cost_impact = CostImpact(
                current_monthly_estimate=cost_data.get("current_monthly", 0),
                post_migration_monthly_estimate=cost_data.get("post_migration_monthly", 0),
                monthly_savings=cost_data.get("monthly_savings", 0),
                annual_savings=cost_data.get("annual_savings", 0),
                one_time_migration_cost=cost_data.get("one_time_cost", 0),
                payback_period_months=cost_data.get("payback_months", 0),
                roi_percentage=cost_data.get("roi_percentage", 0),
                confidence=cost_data.get("confidence", 0.5),
            )

        cloud_readiness = None
        if ai_context.readiness_summary:
            score = ai_context.readiness_summary.get("overall", 0)
            level = "high" if score >= 70 else "moderate" if score >= 40 else "low"
            cloud_readiness = CloudReadinessAssessment(
                overall_score=score,
                readiness_level=level,
            )

        return AIExecutiveSummary(
            project_name=ai_context.project_name,
            overall_modernization_score=ai_context.readiness_summary.get("overall", 50),
            executive_summary=self._generate_summary_text(ai_context),
            cost_impact=cost_impact,
            cloud_readiness=cloud_readiness,
            migration_complexity="moderate",
        )

    def generate_deterministic(self, ai_context: AIContext) -> AIExecutiveSummary:
        profile = get_profile_for_settings()
        risks = []
        for i, gc in enumerate(ai_context.god_classes[:profile.report_max_god_classes]):
            risks.append(BusinessRisk(
                risk_id=f"BR-{i+1:03d}",
                title=f"God Class: {gc.get('name', '')}",
                description=f"Class {gc.get('name', '')} exceeds complexity thresholds with {gc.get('loc', 0)} LOC",
                severity="high",
                impact="Impedes microservice extraction and testing",
                mitigation="Decompose into focused services",
            ))

        for i, cd in enumerate(ai_context.circular_dependencies[:profile.ai_report_max_circular_deps]):
            cycle = cd.get("cycle", [])
            risks.append(BusinessRisk(
                risk_id=f"BR-{len(risks)+1:03d}",
                title=f"Circular Dependency: {' -> '.join(cycle[:profile.report_max_cycle_display])}",
                description=f"Circular dependency chain of length {len(cycle)}",
                severity="high",
                impact="Prevents independent deployment",
                mitigation="Introduce event-driven communication",
            ))

        recommendations = [
            ExecutiveRecommendation(
                title="Begin with low-risk service extraction",
                rationale="Quick wins build team confidence and establish deployment patterns",
                expected_outcome="First microservice deployed and serving traffic",
                priority="high",
                timeline="Weeks 1-4",
                investment_required="2 engineers",
            ),
            ExecutiveRecommendation(
                title="Address god classes before microservice extraction",
                rationale="God classes must be decomposed to enable clean service boundaries",
                expected_outcome="Improved code maintainability",
                priority="high",
                timeline="Weeks 1-8",
                investment_required="2-3 engineers",
            ),
        ]

        score = ai_context.readiness_summary.get("overall", 50)
        grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D" if score >= 35 else "F"

        return AIExecutiveSummary(
            project_name=ai_context.project_name,
            overall_modernization_score=score,
            modernization_grade=grade,
            executive_summary=self._generate_summary_text(ai_context),
            business_risks=risks,
            migration_complexity="moderate",
            estimated_timeline_weeks=16,
            recommendations=recommendations,
            key_metrics={
                "total_classes": ai_context.metrics_summary.get("total_classes", 0),
                "god_classes": len(ai_context.god_classes),
                "circular_deps": len(ai_context.circular_dependencies),
            },
        )

    def _generate_summary_text(self, ctx: AIContext) -> str:
        total = ctx.metrics_summary.get("total_classes", 0)
        god = len(ctx.god_classes)
        circ = len(ctx.circular_dependencies)
        score = ctx.readiness_summary.get("overall", 50)

        return (
            f"The {ctx.project_name} codebase consists of {total} classes "
            f"with {god} god classes and {circ} circular dependency chains. "
            f"The overall modernization readiness score is {score}/100. "
            f"Key priorities include decomposing oversized classes, breaking circular dependencies, "
            f"and establishing a phased migration plan starting with low-coupling services."
        )
