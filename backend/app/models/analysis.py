"""Internal domain model for analysis results."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AnalysisDomain:
    """Internal domain representation of analysis results."""
    job_id: str
    metrics: dict = field(default_factory=dict)
    service_boundaries: list = field(default_factory=list)
    readiness: dict = field(default_factory=dict)
    adrs: list = field(default_factory=list)
    migration_waves: list = field(default_factory=list)
    cost_comparison: dict = field(default_factory=dict)
    explainability: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "metrics": self.metrics,
            "service_boundaries": self.service_boundaries,
            "readiness": self.readiness,
            "adrs": self.adrs,
            "migration_waves": self.migration_waves,
            "cost_comparison": self.cost_comparison,
            "explainability": self.explainability,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisDomain":
        return cls(
            job_id=data["job_id"],
            metrics=data.get("metrics", {}),
            service_boundaries=data.get("service_boundaries", []),
            readiness=data.get("readiness", {}),
            adrs=data.get("adrs", []),
            migration_waves=data.get("migration_waves", []),
            cost_comparison=data.get("cost_comparison", {}),
            explainability=data.get("explainability", {}),
            created_at=data.get("created_at", ""),
        )
