"""Internal domain model for recommendations."""

from dataclasses import dataclass


@dataclass
class RecommendationDomain:
    """Internal domain representation of a recommendation."""
    service_name: str
    primary_reason: str
    secondary_reasons: list[str]
    confidence: float
    migration_complexity: str | None = None
    estimated_effort: str | None = None
