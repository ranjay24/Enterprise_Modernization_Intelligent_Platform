"""AI Recommendation contract — strongly typed recommendation model with explainability."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RecommendationCategory(str, Enum):
    SERVICE_EXTRACTION = "service_extraction"
    DECOMPOSITION = "decomposition"
    REFACTORING = "refactoring"
    DATABASE = "database"
    API_DESIGN = "api_design"
    CLOUD_MIGRATION = "cloud_migration"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COST_OPTIMIZATION = "cost_optimization"
    TESTING = "testing"
    OBSERVABILITY = "observability"
    CICD = "cicd"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"


class RecommendationPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class EvidenceSource:
    """A single piece of evidence supporting a recommendation."""
    source_type: str = ""
    component: str = ""
    detail: str = ""
    metric_value: float | None = None

    def to_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "component": self.component,
            "detail": self.detail,
            "metric_value": self.metric_value,
        }


@dataclass
class ReasoningChain:
    """Step-by-step reasoning behind a recommendation."""
    steps: list[str] = field(default_factory=list)
    conclusion: str = ""
    confidence_factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "steps": self.steps,
            "conclusion": self.conclusion,
            "confidence_factors": self.confidence_factors,
        }


@dataclass
class ExplainabilityData:
    """Full explainability payload for a recommendation."""
    why: str = ""
    evidence_count: int = 0
    evidence_sources: list[EvidenceSource] = field(default_factory=list)
    reasoning_chain: ReasoningChain | None = None
    tradeoffs: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    confidence_reasoning: str = ""
    supporting_metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "why": self.why,
            "evidence_count": self.evidence_count,
            "evidence_sources": [e.to_dict() for e in self.evidence_sources],
            "reasoning_chain": self.reasoning_chain.to_dict() if self.reasoning_chain else None,
            "tradeoffs": self.tradeoffs,
            "alternatives": self.alternatives,
            "confidence_reasoning": self.confidence_reasoning,
            "supporting_metrics": self.supporting_metrics,
        }


@dataclass
class AIRecommendation:
    """A single AI-generated modernization recommendation."""
    recommendation_id: str = field(default_factory=lambda: f"REC-{uuid.uuid4().hex[:8].upper()}")
    title: str = ""
    description: str = ""
    category: RecommendationCategory = RecommendationCategory.ARCHITECTURE
    priority: RecommendationPriority = RecommendationPriority.MEDIUM

    business_value: str = ""
    technical_benefit: str = ""
    migration_difficulty: str = "moderate"
    estimated_effort: str = ""

    confidence: float = 0.5
    evidence: list[EvidenceSource] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    aws_services_involved: list[str] = field(default_factory=list)

    expected_cost_impact: str = ""
    expected_performance_improvement: str = ""

    explainability: ExplainabilityData | None = None

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_id: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "business_value": self.business_value,
            "technical_benefit": self.technical_benefit,
            "migration_difficulty": self.migration_difficulty,
            "estimated_effort": self.estimated_effort,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "dependencies": self.dependencies,
            "aws_services_involved": self.aws_services_involved,
            "expected_cost_impact": self.expected_cost_impact,
            "expected_performance_improvement": self.expected_performance_improvement,
            "explainability": self.explainability.to_dict() if self.explainability else None,
            "created_at": self.created_at,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AIRecommendation:
        explainability = None
        if data.get("explainability"):
            exp = data["explainability"]
            reasoning = None
            if exp.get("reasoning_chain"):
                reasoning = ReasoningChain(**exp["reasoning_chain"])
            explainability = ExplainabilityData(
                why=exp.get("why", ""),
                evidence_count=exp.get("evidence_count", 0),
                evidence_sources=[EvidenceSource(**e) for e in exp.get("evidence_sources", [])],
                reasoning_chain=reasoning,
                tradeoffs=exp.get("tradeoffs", []),
                alternatives=exp.get("alternatives", []),
                confidence_reasoning=exp.get("confidence_reasoning", ""),
                supporting_metrics=exp.get("supporting_metrics", {}),
            )

        return cls(
            recommendation_id=data.get("recommendation_id", f"REC-{uuid.uuid4().hex[:8].upper()}"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            category=RecommendationCategory(data.get("category", "architecture")),
            priority=RecommendationPriority(data.get("priority", "medium")),
            business_value=data.get("business_value", ""),
            technical_benefit=data.get("technical_benefit", ""),
            migration_difficulty=data.get("migration_difficulty", "moderate"),
            estimated_effort=data.get("estimated_effort", ""),
            confidence=data.get("confidence", 0.5),
            evidence=[EvidenceSource(**e) for e in data.get("evidence", [])],
            dependencies=data.get("dependencies", []),
            aws_services_involved=data.get("aws_services_involved", []),
            expected_cost_impact=data.get("expected_cost_impact", ""),
            expected_performance_improvement=data.get("expected_performance_improvement", ""),
            explainability=explainability,
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            model_id=data.get("model_id", ""),
            prompt_version=data.get("prompt_version", ""),
        )
