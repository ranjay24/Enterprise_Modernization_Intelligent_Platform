"""AnalysisContext — shared mutable state flowing through the analysis pipeline."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisContext:
    """Shared context passed to every analyzer. Analyzers enrich it in place."""

    job_id: str
    extracted_path: str
    start_time: float = field(default_factory=time.time)

    project_metadata: dict | None = None
    parsed_classes: list[Any] = field(default_factory=list)
    parsed_interfaces: list[Any] = field(default_factory=list)
    parsed_enums: list[Any] = field(default_factory=list)
    endpoints: list[Any] = field(default_factory=list)
    annotations_index: dict[str, list[str]] = field(default_factory=dict)

    dependency_graph: dict | None = None
    circular_dependencies: list[dict] = field(default_factory=list)
    coupling_analysis: dict | None = None

    metrics: dict[str, Any] = field(default_factory=dict)
    quality_metrics: dict[str, Any] = field(default_factory=dict)

    architecture_style: dict | None = None
    architecture_scores: dict[str, float] = field(default_factory=dict)

    risk_findings: list[dict] = field(default_factory=list)
    risk_summary: dict | None = None

    readiness_scores: dict[str, Any] = field(default_factory=dict)
    readiness_dimensions: dict[str, dict] = field(default_factory=dict)

    recommendations: list[dict] = field(default_factory=list)

    graph_data: dict[str, Any] = field(default_factory=dict)

    events: list[dict] = field(default_factory=list)

    errors: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def elapsed_seconds(self) -> float:
        return round(time.time() - self.start_time, 3)

    @property
    def class_count(self) -> int:
        return len(self.parsed_classes)

    @property
    def package_names(self) -> set[str]:
        return {getattr(c, "package", "") for c in self.parsed_classes if getattr(c, "package", "")}

    def has_phase(self, phase_name: str) -> bool:
        return phase_name in self.metadata

    def set_phase(self, phase_name: str, result: Any = None) -> None:
        self.metadata[phase_name] = {
            "completed": True,
            "result": result,
            "timestamp": time.time(),
        }

    def add_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        self.events.append({
            "event_type": event_type,
            "data": data or {},
            "timestamp": time.time(),
        })

    def add_error(self, analyzer: str, message: str, details: Any = None) -> None:
        self.errors.append({
            "analyzer": analyzer,
            "message": message,
            "details": details,
            "timestamp": time.time(),
        })

    def to_dict(self) -> dict[str, Any]:
        """Serialize context for storage or debugging."""
        return {
            "job_id": self.job_id,
            "elapsed_seconds": self.elapsed_seconds,
            "class_count": self.class_count,
            "package_count": len(self.package_names),
            "phases_completed": list(self.metadata.keys()),
            "events_count": len(self.events),
            "errors_count": len(self.errors),
            "metrics_keys": list(self.metrics.keys()),
            "has_dependency_graph": self.dependency_graph is not None,
            "has_architecture": self.architecture_style is not None,
            "risk_count": len(self.risk_findings),
            "recommendation_count": len(self.recommendations),
        }
