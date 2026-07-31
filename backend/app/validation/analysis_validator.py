"""Analysis Validator — post-assembly validation engine ensuring internal consistency."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    check_name: str
    passed: bool
    expected: Any
    actual: Any
    message: str

    def to_dict(self) -> dict:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
        }


class AnalysisValidator:
    """Validates structural and numeric consistency across assembled pipeline results."""

    def validate(self, results: dict) -> list[ValidationResult]:
        checks = []
        checks.extend(self._validate_endpoint_totals(results))
        checks.extend(self._validate_class_ownership(results))
        checks.extend(self._validate_entity_ownership(results))
        checks.extend(self._validate_migration_consistency(results))
        checks.extend(self._validate_boundary_completeness(results))
        checks.extend(self._validate_no_duplicate_services(results))
        checks.extend(self._validate_metric_consistency(results))
        checks.extend(self._validate_cost_consistency(results))
        return checks

    def _validate_endpoint_totals(self, results: dict):
        boundaries = results.get("service_boundaries", []) or []
        attributed = sum(len(b.get("api_endpoints", []) or []) for b in boundaries)
        total = results.get("metrics", {}).get("total_endpoints", 0)
        passed = (attributed == total) or (total == 0)
        yield ValidationResult(
            "endpoint_totals",
            passed,
            total,
            attributed,
            f"Endpoint total match: {attributed} attributed across boundaries vs {total} total"
            if passed
            else f"Endpoint total mismatch: {attributed} attributed vs {total} total in static analysis",
        )

    def _validate_class_ownership(self, results: dict):
        boundaries = results.get("service_boundaries", []) or []
        seen = set()
        duplicates = set()
        for b in boundaries:
            for cn in b.get("classes", []) or []:
                if cn in seen:
                    duplicates.add(cn)
                seen.add(cn)
        passed = len(duplicates) == 0
        yield ValidationResult(
            "class_ownership",
            passed,
            0,
            len(duplicates),
            "Single class ownership verified across all boundaries"
            if passed
            else f"Duplicate class ownership detected for: {', '.join(sorted(duplicates))}",
        )

    def _validate_entity_ownership(self, results: dict):
        boundaries = results.get("service_boundaries", []) or []
        entity_owners: dict[str, list[str]] = {}
        for b in boundaries:
            for table in b.get("database_tables", []) or []:
                entity_owners.setdefault(table, []).append(b.get("name", ""))
        shared = {t: s for t, s in entity_owners.items() if len(s) > 1}
        passed = len(shared) == 0
        yield ValidationResult(
            "entity_table_ownership",
            passed,
            0,
            len(shared),
            "Single database table ownership verified"
            if passed
            else f"Shared database tables detected: {shared}",
        )

    def _validate_migration_consistency(self, results: dict):
        waves = results.get("migration_waves", []) or []
        if not waves:
            yield ValidationResult("migration_weeks", True, 0, 0, "No migration waves present")
            return
        total_weeks = sum(w.get("timeline_weeks", 0) for w in waves)
        reported = results.get("migration_impact", {}).get("estimated_timeline_weeks", total_weeks)
        passed = (total_weeks == reported)
        yield ValidationResult(
            "migration_weeks",
            passed,
            reported,
            total_weeks,
            f"Migration roadmap timeline matches wave sum ({total_weeks} weeks)"
            if passed
            else f"Migration roadmap mismatch: summary states {reported} weeks, waves sum to {total_weeks} weeks",
        )

    def _validate_boundary_completeness(self, results: dict):
        boundaries = results.get("service_boundaries", []) or []
        empty = [b.get("name", "") for b in boundaries if not (b.get("classes", []) or [])]
        passed = len(empty) == 0
        yield ValidationResult(
            "boundary_completeness",
            passed,
            0,
            len(empty),
            "All service boundaries contain assigned classes"
            if passed
            else f"Empty service boundaries detected: {empty}",
        )

    def _validate_no_duplicate_services(self, results: dict):
        boundaries = results.get("service_boundaries", []) or []
        names = [b.get("name", "") for b in boundaries]
        unique_names = set(names)
        passed = (len(names) == len(unique_names))
        yield ValidationResult(
            "no_duplicate_services",
            passed,
            len(names),
            len(unique_names),
            "Service boundary names are unique"
            if passed
            else f"Duplicate service boundary names detected: {names}",
        )

    def _validate_metric_consistency(self, results: dict):
        total_classes = results.get("metrics", {}).get("total_classes", 0)
        boundaries = results.get("service_boundaries", []) or []
        assigned = sum(len(b.get("classes", []) or []) for b in boundaries)
        passed = (total_classes >= assigned)
        yield ValidationResult(
            "metric_consistency",
            passed,
            f">= {assigned}",
            total_classes,
            f"Total classes ({total_classes}) encompasses assigned boundary classes ({assigned})"
            if passed
            else f"Class count discrepancy: {total_classes} total vs {assigned} assigned",
        )

    def _validate_cost_consistency(self, results: dict):
        cost = results.get("cost_comparison", {}) or {}
        if not cost:
            yield ValidationResult("cost_consistency", True, 0, 0, "No cost comparison data present")
            return
        curr = cost.get("current_monthly", 0)
        post = cost.get("post_migration_monthly", 0)
        sav = cost.get("monthly_savings", 0)
        expected = round(curr - post, 2)
        passed = abs(sav - expected) <= 0.05
        yield ValidationResult(
            "cost_consistency",
            passed,
            expected,
            sav,
            f"Monthly savings ({sav}) matches baseline difference ({curr} - {post})"
            if passed
            else f"Cost savings discrepancy: reported {sav}, expected {expected}",
        )
