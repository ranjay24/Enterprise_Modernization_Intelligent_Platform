"""Analysis quality score aggregator."""

from __future__ import annotations
import structlog
from app.validation.analysis_validator import ValidationResult

logger = structlog.get_logger(__name__)


def compute_analysis_quality(validation_results: list[ValidationResult]) -> dict:
    """Aggregate validation results into an overall analysis quality score."""
    if not validation_results:
        return {
            "quality_score": 100,
            "checks_passed": 0,
            "checks_total": 0,
            "checks_failed": [],
            "reliability": "high",
        }

    passed = sum(1 for r in validation_results if r.passed)
    total = len(validation_results)
    score = round((passed / total) * 100)
    failed = [r.to_dict() for r in validation_results if not r.passed]

    reliability = "high" if passed == total else "medium" if (passed / total) >= 0.8 else "low"

    return {
        "quality_score": score,
        "checks_passed": passed,
        "checks_total": total,
        "checks_failed": failed,
        "reliability": reliability,
    }
