"""AnalysisResult — final structured output from the analysis engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AnalysisResult:
    """Immutable final result from a complete analysis run."""

    job_id: str
    analysis_version: str = "2.0.0"
    engine_version: str = "1.0.0"
    rules_version: str = "1.0.0"

    project_summary: dict[str, Any] = field(default_factory=dict)
    architecture_summary: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    quality_metrics: dict[str, Any] = field(default_factory=dict)
    readiness_scores: dict[str, Any] = field(default_factory=dict)
    readiness_dimensions: dict[str, dict] = field(default_factory=dict)
    risk_report: dict[str, Any] = field(default_factory=dict)
    dependency_graph: dict[str, Any] = field(default_factory=dict)
    coupling_analysis: dict[str, Any] = field(default_factory=dict)
    architecture_graph: dict[str, Any] = field(default_factory=dict)
    candidate_services: list[dict] = field(default_factory=list)
    bounded_contexts: list[dict] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)

    confidence_scores: dict[str, float] = field(default_factory=dict)
    overall_modernization_score: float = 0.0
    migration_complexity: str = "unknown"

    analysis_duration_ms: float = 0.0
    memory_usage_mb: float = 0.0
    phases_completed: list[str] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    graph_data: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON storage."""
        return {
            "job_id": self.job_id,
            "analysis_version": self.analysis_version,
            "engine_version": self.engine_version,
            "rules_version": self.rules_version,
            "project_summary": self.project_summary,
            "architecture_summary": self.architecture_summary,
            "metrics": self.metrics,
            "quality_metrics": self.quality_metrics,
            "readiness_scores": self.readiness_scores,
            "readiness_dimensions": self.readiness_dimensions,
            "risk_report": self.risk_report,
            "dependency_graph": self.dependency_graph,
            "coupling_analysis": self.coupling_analysis,
            "architecture_graph": self.architecture_graph,
            "candidate_services": self.candidate_services,
            "bounded_contexts": self.bounded_contexts,
            "recommendations": self.recommendations,
            "confidence_scores": self.confidence_scores,
            "overall_modernization_score": self.overall_modernization_score,
            "migration_complexity": self.migration_complexity,
            "analysis_duration_ms": self.analysis_duration_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "phases_completed": self.phases_completed,
            "errors": self.errors,
            "graph_data": self.graph_data,
            "created_at": self.created_at,
        }
