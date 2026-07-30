"""AI Developer Report contract — strongly typed developer report model."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ArchitectureFinding:
    """An architecture finding for developers."""
    finding_id: str = ""
    category: str = ""
    title: str = ""
    description: str = ""
    affected_components: list[str] = field(default_factory=list)
    severity: str = "info"
    recommendation: str = ""
    reference: str = ""

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "affected_components": self.affected_components,
            "severity": self.severity,
            "recommendation": self.recommendation,
            "reference": self.reference,
        }


@dataclass
class DependencyAnalysis:
    """Dependency analysis findings."""
    total_dependencies: int = 0
    circular_dependencies: int = 0
    highly_coupled_classes: list[dict] = field(default_factory=list)
    package_dependencies: dict = field(default_factory=dict)
    coupling_hotspots: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_dependencies": self.total_dependencies,
            "circular_dependencies": self.circular_dependencies,
            "highly_coupled_classes": self.highly_coupled_classes,
            "package_dependencies": self.package_dependencies,
            "coupling_hotspots": self.coupling_hotspots,
            "recommendations": self.recommendations,
        }


@dataclass
class CodeQualityAssessment:
    """Code quality assessment for developers."""
    overall_score: float = 0.0
    maintainability_score: float = 0.0
    complexity_score: float = 0.0
    technical_debt_hours: float = 0.0
    duplication_percent: float = 0.0
    god_class_count: int = 0
    long_method_count: int = 0
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "maintainability_score": self.maintainability_score,
            "complexity_score": self.complexity_score,
            "technical_debt_hours": self.technical_debt_hours,
            "duplication_percent": self.duplication_percent,
            "god_class_count": self.god_class_count,
            "long_method_count": self.long_method_count,
            "issues": self.issues,
        }


@dataclass
class TechnicalDebtItem:
    """A specific technical debt item."""
    debt_id: str = ""
    title: str = ""
    category: str = ""
    description: str = ""
    estimated_effort_hours: float = 0.0
    priority: str = "medium"
    affected_components: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "debt_id": self.debt_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "estimated_effort_hours": self.estimated_effort_hours,
            "priority": self.priority,
            "affected_components": self.affected_components,
        }


@dataclass
class MigrationOpportunity:
    """A migration opportunity for developers."""
    opportunity_id: str = ""
    title: str = ""
    description: str = ""
    source_classes: list[str] = field(default_factory=list)
    target_pattern: str = ""
    difficulty: str = "moderate"
    business_value: str = ""
    technical_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "description": self.description,
            "source_classes": self.source_classes,
            "target_pattern": self.target_pattern,
            "difficulty": self.difficulty,
            "business_value": self.business_value,
            "technical_steps": self.technical_steps,
        }


@dataclass
class AWSServiceRecommendation:
    """An AWS service recommendation."""
    service_name: str = ""
    use_case: str = ""
    justification: str = ""
    alternatives: list[str] = field(default_factory=list)
    pricing_model: str = ""
    free_tier_eligible: bool = False

    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "use_case": self.use_case,
            "justification": self.justification,
            "alternatives": self.alternatives,
            "pricing_model": self.pricing_model,
            "free_tier_eligible": self.free_tier_eligible,
        }


@dataclass
class AIDeveloperReport:
    """Complete AI-generated developer report."""
    report_id: str = field(default_factory=lambda: f"DR-{uuid.uuid4().hex[:8].upper()}")
    project_name: str = ""
    architecture_findings: list[ArchitectureFinding] = field(default_factory=list)
    dependency_analysis: DependencyAnalysis | None = None
    code_quality: CodeQualityAssessment | None = None
    technical_debt: list[TechnicalDebtItem] = field(default_factory=list)
    risk_assessment: list[dict] = field(default_factory=list)
    migration_opportunities: list[MigrationOpportunity] = field(default_factory=list)
    aws_service_recommendations: list[AWSServiceRecommendation] = field(default_factory=list)
    key_findings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_id: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "project_name": self.project_name,
            "architecture_findings": [f.to_dict() for f in self.architecture_findings],
            "dependency_analysis": self.dependency_analysis.to_dict() if self.dependency_analysis else None,
            "code_quality": self.code_quality.to_dict() if self.code_quality else None,
            "technical_debt": [d.to_dict() for d in self.technical_debt],
            "risk_assessment": self.risk_assessment,
            "migration_opportunities": [o.to_dict() for o in self.migration_opportunities],
            "aws_service_recommendations": [r.to_dict() for r in self.aws_service_recommendations],
            "key_findings": self.key_findings,
            "created_at": self.created_at,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AIDeveloperReport:
        dep_analysis = DependencyAnalysis(**data["dependency_analysis"]) if data.get("dependency_analysis") else None
        code_quality = CodeQualityAssessment(**data["code_quality"]) if data.get("code_quality") else None

        return cls(
            report_id=data.get("report_id", f"DR-{uuid.uuid4().hex[:8].upper()}"),
            project_name=data.get("project_name", ""),
            architecture_findings=[ArchitectureFinding(**f) for f in data.get("architecture_findings", [])],
            dependency_analysis=dep_analysis,
            code_quality=code_quality,
            technical_debt=[TechnicalDebtItem(**d) for d in data.get("technical_debt", [])],
            risk_assessment=data.get("risk_assessment", []),
            migration_opportunities=[MigrationOpportunity(**o) for o in data.get("migration_opportunities", [])],
            aws_service_recommendations=[AWSServiceRecommendation(**r) for r in data.get("aws_service_recommendations", [])],
            key_findings=data.get("key_findings", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            model_id=data.get("model_id", ""),
            prompt_version=data.get("prompt_version", ""),
        )
