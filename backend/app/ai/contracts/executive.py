"""AI Executive Summary contract — strongly typed executive report model."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class BusinessRisk:
    """A business-level risk."""
    risk_id: str = ""
    title: str = ""
    description: str = ""
    severity: str = "medium"
    likelihood: str = "medium"
    impact: str = ""
    mitigation: str = ""

    def to_dict(self) -> dict:
        return {
            "risk_id": self.risk_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "likelihood": self.likelihood,
            "impact": self.impact,
            "mitigation": self.mitigation,
        }


@dataclass
class CostImpact:
    """Cost impact assessment."""
    current_monthly_estimate: float = 0.0
    post_migration_monthly_estimate: float = 0.0
    monthly_savings: float = 0.0
    annual_savings: float = 0.0
    one_time_migration_cost: float = 0.0
    payback_period_months: int = 0
    roi_percentage: float = 0.0
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "current_monthly_estimate": self.current_monthly_estimate,
            "post_migration_monthly_estimate": self.post_migration_monthly_estimate,
            "monthly_savings": self.monthly_savings,
            "annual_savings": self.annual_savings,
            "one_time_migration_cost": self.one_time_migration_cost,
            "payback_period_months": self.payback_period_months,
            "roi_percentage": self.roi_percentage,
            "confidence": self.confidence,
        }


@dataclass
class CloudReadinessAssessment:
    """Cloud readiness high-level assessment."""
    overall_score: float = 0.0
    readiness_level: str = "moderate"
    key_blockers: list[str] = field(default_factory=list)
    quick_wins: list[str] = field(default_factory=list)
    estimated_cloud_benefits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "readiness_level": self.readiness_level,
            "key_blockers": self.key_blockers,
            "quick_wins": self.quick_wins,
            "estimated_cloud_benefits": self.estimated_cloud_benefits,
        }


@dataclass
class ExecutiveRecommendation:
    """A high-level recommendation for executives."""
    title: str = ""
    rationale: str = ""
    expected_outcome: str = ""
    priority: str = "medium"
    timeline: str = ""
    investment_required: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "rationale": self.rationale,
            "expected_outcome": self.expected_outcome,
            "priority": self.priority,
            "timeline": self.timeline,
            "investment_required": self.investment_required,
        }


@dataclass
class AIExecutiveSummary:
    """Complete AI-generated executive summary."""
    summary_id: str = field(default_factory=lambda: f"ES-{uuid.uuid4().hex[:8].upper()}")
    project_name: str = ""
    overall_modernization_score: float = 0.0
    modernization_grade: str = "C"
    executive_summary: str = ""
    business_risks: list[BusinessRisk] = field(default_factory=list)
    cost_impact: CostImpact | None = None
    cloud_readiness: CloudReadinessAssessment | None = None
    migration_complexity: str = "moderate"
    estimated_timeline_weeks: int = 0
    recommendations: list[ExecutiveRecommendation] = field(default_factory=list)
    key_metrics: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_id: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "summary_id": self.summary_id,
            "project_name": self.project_name,
            "overall_modernization_score": self.overall_modernization_score,
            "modernization_grade": self.modernization_grade,
            "executive_summary": self.executive_summary,
            "business_risks": [r.to_dict() for r in self.business_risks],
            "cost_impact": self.cost_impact.to_dict() if self.cost_impact else None,
            "cloud_readiness": self.cloud_readiness.to_dict() if self.cloud_readiness else None,
            "migration_complexity": self.migration_complexity,
            "estimated_timeline_weeks": self.estimated_timeline_weeks,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "key_metrics": self.key_metrics,
            "created_at": self.created_at,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AIExecutiveSummary:
        cost_impact = CostImpact(**data["cost_impact"]) if data.get("cost_impact") else None
        cloud_readiness = CloudReadinessAssessment(**data["cloud_readiness"]) if data.get("cloud_readiness") else None

        return cls(
            summary_id=data.get("summary_id", f"ES-{uuid.uuid4().hex[:8].upper()}"),
            project_name=data.get("project_name", ""),
            overall_modernization_score=data.get("overall_modernization_score", 0.0),
            modernization_grade=data.get("modernization_grade", "C"),
            executive_summary=data.get("executive_summary", ""),
            business_risks=[BusinessRisk(**r) for r in data.get("business_risks", [])],
            cost_impact=cost_impact,
            cloud_readiness=cloud_readiness,
            migration_complexity=data.get("migration_complexity", "moderate"),
            estimated_timeline_weeks=data.get("estimated_timeline_weeks", 0),
            recommendations=[ExecutiveRecommendation(**r) for r in data.get("recommendations", [])],
            key_metrics=data.get("key_metrics", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            model_id=data.get("model_id", ""),
            prompt_version=data.get("prompt_version", ""),
        )
