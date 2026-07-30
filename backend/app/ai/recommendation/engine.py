"""AI Recommendation Engine — generates structured recommendations with explainability."""

from __future__ import annotations

import structlog

from app.ai.context.builder import AIContext
from app.ai.contracts.recommendation import (
    AIRecommendation,
    EvidenceSource,
    ExplainabilityData,
    ReasoningChain,
    RecommendationCategory,
    RecommendationPriority,
)

logger = structlog.get_logger(__name__)


class AIRecommendationEngine:
    """Generates AI-powered modernization recommendations.

    Takes AIContext (from Sprint 2 analysis) and produces structured
    AIRecommendation objects with full explainability.
    """

    def __init__(self, provider_registry=None, pipeline=None):
        self._registry = provider_registry
        self._pipeline = pipeline

    def generate(self, ai_context: AIContext, parsed_response: dict) -> list[AIRecommendation]:
        """Generate recommendations from a parsed AI response."""
        recommendations = []

        for rec_data in parsed_response.get("recommendations", []):
            try:
                recommendation = self._build_recommendation(rec_data)
                recommendations.append(recommendation)
            except Exception as exc:
                logger.warning("recommendation_build_failed", error=str(exc))

        return sorted(recommendations, key=lambda r: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.priority.value, 4),
            -r.confidence,
        ))

    def generate_deterministic(self, ai_context: AIContext) -> list[AIRecommendation]:
        """Generate recommendations without AI — fallback using Sprint 2 data.

        Used when AI invocation fails or is unavailable.
        """
        recommendations = []

        if ai_context.recommendations:
            for rec in ai_context.recommendations:
                try:
                    recommendation = AIRecommendation(
                        title=rec.get("title", ""),
                        description=rec.get("description", ""),
                        category=RecommendationCategory(rec.get("category", "architecture")),
                        priority=RecommendationPriority(rec.get("priority", "medium")),
                        business_value=rec.get("business_value", ""),
                        technical_benefit=rec.get("technical_benefit", ""),
                        migration_difficulty=rec.get("migration_difficulty", "moderate"),
                        estimated_effort=rec.get("estimated_effort", ""),
                        confidence=rec.get("confidence", 0.5),
                        evidence=[
                            EvidenceSource(source_type="static_analysis", detail=e)
                            for e in rec.get("evidence", [])
                        ],
                        explainability=ExplainabilityData(
                            why=rec.get("description", ""),
                            evidence_count=len(rec.get("evidence", [])),
                            reasoning_chain=ReasoningChain(
                                steps=["Static analysis identified pattern", "Pattern matches migration opportunity"],
                                conclusion=rec.get("title", ""),
                            ),
                            tradeoffs=["Requires testing", "Team training needed"],
                            alternatives=["Refactor in place", "Gradual migration"],
                        ),
                    )
                    recommendations.append(recommendation)
                except Exception as exc:
                    logger.warning("deterministic_recommendation_failed", error=str(exc))

        if not recommendations:
            recommendations = self._derive_from_context(ai_context)

        return recommendations

    def _derive_from_context(self, ctx: AIContext) -> list[AIRecommendation]:
        """Derive recommendations from risk findings and architecture when no explicit recommendations exist."""
        recommendations = []

        for finding in ctx.risk_findings:
            severity = finding.get("severity", "medium")
            rec = AIRecommendation(
                title=f"Address {finding.get('title', 'risk finding')}",
                description=finding.get("description", ""),
                category=RecommendationCategory("architecture"),
                priority=RecommendationPriority(severity if severity in ("critical", "high", "medium", "low") else "medium"),
                business_value="Improves system reliability and maintainability",
                technical_benefit=finding.get("description", ""),
                migration_difficulty="moderate",
                estimated_effort="2-4 weeks",
                confidence=0.6,
                evidence=[
                    EvidenceSource(source_type="static_analysis", detail=f"Rule {finding.get('rule_id', '')} triggered")
                ],
                explainability=ExplainabilityData(
                    why=finding.get("description", ""),
                    evidence_count=1,
                    reasoning_chain=ReasoningChain(
                        steps=[f"Risk rule {finding.get('rule_id', '')} identified issue", "Recommendation derived from risk analysis"],
                        conclusion=f"Address {finding.get('title', 'issue')}",
                    ),
                    tradeoffs=["Requires testing", "Team training needed"],
                    alternatives=["Refactor in place", "Gradual migration"],
                ),
            )
            recommendations.append(rec)

        if ctx.god_classes:
            rec = AIRecommendation(
                title="Decompose God Classes",
                description=f"Found {len(ctx.god_classes)} god classes that should be decomposed",
                category=RecommendationCategory("architecture"),
                priority=RecommendationPriority("high"),
                business_value="Reduces technical debt and improves maintainability",
                technical_benefit="Smaller, focused classes are easier to test, maintain, and migrate",
                migration_difficulty="moderate",
                estimated_effort="3-6 weeks per class",
                confidence=0.8,
                evidence=[
                    EvidenceSource(source_type="static_analysis", detail=f"God class: {g.get('name', '')} ({g.get('loc', 0)} LOC)")
                    for g in ctx.god_classes
                ],
                explainability=ExplainabilityData(
                    why=f"{len(ctx.god_classes)} classes exceed complexity thresholds",
                    evidence_count=len(ctx.god_classes),
                    reasoning_chain=ReasoningChain(
                        steps=["Identified god classes via metrics", "God classes resist decomposition into services"],
                        conclusion="Decompose before migration",
                    ),
                    tradeoffs=["Risk of regression", "Requires comprehensive testing"],
                    alternatives=["Gradual extraction", "Wrap as service first"],
                ),
            )
            recommendations.append(rec)

        if ctx.circular_dependencies:
            rec = AIRecommendation(
                title="Break Circular Dependencies",
                description=f"Found {len(ctx.circular_dependencies)} circular dependency chains",
                category=RecommendationCategory("architecture"),
                priority=RecommendationPriority("high"),
                business_value="Enables independent service deployment",
                technical_benefit="Breaking cycles allows clean service boundaries",
                migration_difficulty="hard",
                estimated_effort="2-4 weeks",
                confidence=0.75,
                evidence=[
                    EvidenceSource(source_type="static_analysis", detail=f"Cycle: {' → '.join(c.get('cycle', []))}")
                    for c in ctx.circular_dependencies
                ],
                explainability=ExplainabilityData(
                    why="Circular dependencies prevent clean service extraction",
                    evidence_count=len(ctx.circular_dependencies),
                    reasoning_chain=ReasoningChain(
                        steps=["Mapped dependency graph", "Identified circular chains", "Circular deps prevent independent deployment"],
                        conclusion="Break cycles before service extraction",
                    ),
                    tradeoffs=["May require interface extraction", "Could affect runtime behavior"],
                    alternatives=["Dependency inversion", "Shared kernel pattern"],
                ),
            )
            recommendations.append(rec)

        if ctx.candidate_services:
            rec = AIRecommendation(
                title=f"Extract {len(ctx.candidate_services)} Candidate Services",
                description=" identified candidate services ready for extraction",
                category=RecommendationCategory("architecture"),
                priority=RecommendationPriority("medium"),
                business_value="Incremental migration reduces risk",
                technical_benefit="Services can be deployed and scaled independently",
                migration_difficulty="moderate",
                estimated_effort="1-2 weeks per service",
                confidence=0.7,
                evidence=[
                    EvidenceSource(source_type="static_analysis", detail=f"Service: {s.get('name', '')}")
                    for s in ctx.candidate_services
                ],
                explainability=ExplainabilityData(
                    why="Candidate services identified via architecture analysis",
                    evidence_count=len(ctx.candidate_services),
                    reasoning_chain=ReasoningChain(
                        steps=["Analyzed package structure", "Identified cohesion boundaries"],
                        conclusion=f"Extract {len(ctx.candidate_services)} services",
                    ),
                    tradeoffs=["Requires API design", "Team coordination needed"],
                    alternatives=["Monolith refactoring first", "Strangler fig pattern"],
                ),
            )
            recommendations.append(rec)

        return recommendations

    def _build_recommendation(self, data: dict) -> AIRecommendation:
        """Build an AIRecommendation from parsed response data."""
        explainability = None
        if data.get("explainability"):
            exp = data["explainability"]
            reasoning = None
            if exp.get("reasoning_chain"):
                reasoning = ReasoningChain(
                    steps=exp["reasoning_chain"].get("steps", []),
                    conclusion=exp["reasoning_chain"].get("conclusion", ""),
                    confidence_factors=exp["reasoning_chain"].get("confidence_factors", []),
                )
            explainability = ExplainabilityData(
                why=exp.get("why", ""),
                evidence_count=exp.get("evidence_count", 0),
                evidence_sources=[
                    EvidenceSource(
                        source_type=e.get("source_type", ""),
                        component=e.get("component", ""),
                        detail=e.get("detail", ""),
                        metric_value=e.get("metric_value"),
                    )
                    for e in exp.get("evidence_sources", [])
                ],
                reasoning_chain=reasoning,
                tradeoffs=exp.get("tradeoffs", []),
                alternatives=exp.get("alternatives", []),
                confidence_reasoning=exp.get("confidence_reasoning", ""),
                supporting_metrics=exp.get("supporting_metrics", {}),
            )

        evidence = [
            EvidenceSource(
                source_type=e.get("source_type", "analysis"),
                component=e.get("component", ""),
                detail=e.get("detail", ""),
                metric_value=e.get("metric_value"),
            )
            for e in data.get("evidence", [])
        ]

        return AIRecommendation(
            recommendation_id=data.get("recommendation_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            category=RecommendationCategory(data.get("category", "architecture")),
            priority=RecommendationPriority(data.get("priority", "medium")),
            business_value=data.get("business_value", ""),
            technical_benefit=data.get("technical_benefit", ""),
            migration_difficulty=data.get("migration_difficulty", "moderate"),
            estimated_effort=data.get("estimated_effort", ""),
            confidence=float(data.get("confidence", 0.5)),
            evidence=evidence,
            dependencies=data.get("dependencies", []),
            aws_services_involved=data.get("aws_services_involved", []),
            expected_cost_impact=data.get("expected_cost_impact", ""),
            expected_performance_improvement=data.get("expected_performance_improvement", ""),
            explainability=explainability,
        )
