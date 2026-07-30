"""Cloud Readiness Engine — evaluates 8 dimensions and produces readiness report."""

from __future__ import annotations

import structlog

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext
from app.analysis.events.bus import EventType
from app.analysis.readiness.dimensions import (
    score_cicd_readiness,
    score_compute_readiness,
    score_configuration_readiness,
    score_container_readiness,
    score_database_readiness,
    score_networking_readiness,
    score_observability_readiness,
    score_security_readiness,
)

logger = structlog.get_logger(__name__)

DIMENSIONS = {
    "compute_readiness": ("Compute Readiness", score_compute_readiness),
    "database_readiness": ("Database Readiness", score_database_readiness),
    "networking_readiness": ("Networking Readiness", score_networking_readiness),
    "configuration_readiness": ("Configuration Readiness", score_configuration_readiness),
    "security_readiness": ("Security Readiness", score_security_readiness),
    "container_readiness": ("Container Readiness", score_container_readiness),
    "cicd_readiness": ("CI/CD Readiness", score_cicd_readiness),
    "observability_readiness": ("Observability Readiness", score_observability_readiness),
}


class CloudReadinessAnalyzer(Analyzer):
    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="cloud_readiness", version="1.0.0", phase=AnalyzerPhase.READINESS,
            description="Evaluates cloud readiness across 8 dimensions (0-100 each)",
            tags=["readiness", "cloud", "scoring"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return "overall" not in context.readiness_scores

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        logger.info("calculating_readiness")
        metrics = context.metrics
        dimensions: dict[str, dict] = {}
        scores: list[float] = []

        weights = {
            "compute_readiness": 0.20, "database_readiness": 0.15, "networking_readiness": 0.10,
            "configuration_readiness": 0.10, "security_readiness": 0.15, "container_readiness": 0.15,
            "cicd_readiness": 0.10, "observability_readiness": 0.05,
        }

        for key, (label, scorer) in DIMENSIONS.items():
            result = scorer(metrics, context)
            dimensions[key] = {"label": label, "score": result["score"], "reasons": result["reasons"]}
            scores.append(result["score"])

        overall = round(sum(s * weights[k] for k, s in zip(DIMENSIONS.keys(), scores)) / sum(weights.values()), 1) if scores else 0

        context.readiness_scores = {
            "overall": overall,
            "compute": dimensions.get("compute_readiness", {}).get("score", 0),
            "database": dimensions.get("database_readiness", {}).get("score", 0),
            "networking": dimensions.get("networking_readiness", {}).get("score", 0),
            "configuration": dimensions.get("configuration_readiness", {}).get("score", 0),
            "security": dimensions.get("security_readiness", {}).get("score", 0),
            "container": dimensions.get("container_readiness", {}).get("score", 0),
            "cicd": dimensions.get("cicd_readiness", {}).get("score", 0),
            "observability": dimensions.get("observability_readiness", {}).get("score", 0),
            "confidence": 0.75,
            "summary": self._generate_summary(overall, dimensions),
        }
        context.readiness_dimensions = dimensions

        context.add_event(EventType.READINESS_CALCULATED.value, {"overall": overall})
        context.set_phase("readiness")

        logger.info("readiness_calculated", overall=overall)
        return context

    def _generate_summary(self, overall: float, dimensions: dict) -> str:
        if overall >= 75:
            return "Application shows strong cloud readiness. Minor refinements needed."
        if overall >= 50:
            return "Moderate cloud readiness. Several areas need improvement before cloud migration."
        if overall >= 25:
            return "Low cloud readiness. Significant refactoring recommended before migration."
        return "Very low cloud readiness. Major architectural changes required."
