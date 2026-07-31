"""Evidence-based confidence calculator for service boundaries."""

from __future__ import annotations
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ConfidenceFactor:
    name: str
    weight: float
    score: float  # 0.0 - 1.0
    evidence: str


class ConfidenceCalculator:
    """Calculates deterministic, evidence-backed confidence scores for boundaries."""

    FACTORS = {
        "ddd_chain_completeness": 0.25,
        "boundary_isolation": 0.20,
        "entity_ownership": 0.15,
        "endpoint_clarity": 0.10,
        "package_alignment": 0.10,
        "dependency_health": 0.10,
        "static_completeness": 0.10,
    }

    def calculate(
        self, boundary: dict, class_by_name: dict, all_endpoints: list[dict] | None = None
    ) -> tuple[int, list[ConfidenceFactor]]:
        factors = []
        for name, weight in self.FACTORS.items():
            score, evidence = getattr(self, f"_score_{name}")(boundary, class_by_name, all_endpoints)
            factors.append(ConfidenceFactor(name, weight, score, evidence))
        total = sum(f.weight * f.score for f in factors)
        return round(total * 100), factors

    def _score_ddd_chain_completeness(
        self, boundary: dict, class_by_name: dict, all_endpoints: list[dict] | None
    ) -> tuple[float, str]:
        classes = set(boundary.get("classes", []) or [])
        has_ctrl = any(class_by_name.get(c, {}).get("is_controller") for c in classes)
        has_svc = any(class_by_name.get(c, {}).get("is_service") for c in classes)
        has_repo = any(
            class_by_name.get(c, {}).get("is_repository")
            or class_by_name.get(c, {}).get("name", "").endswith("Repository")
            for c in classes
        )
        has_ent = any(class_by_name.get(c, {}).get("is_entity") for c in classes)
        count = sum([has_ctrl, has_svc, has_repo, has_ent])
        score_map = {4: 1.0, 3: 0.75, 2: 0.5, 1: 0.25, 0: 0.0}
        score = score_map.get(count, 0.0)
        roles = []
        if has_ctrl: roles.append("Controller")
        if has_svc: roles.append("Service")
        if has_repo: roles.append("Repository")
        if has_ent: roles.append("Entity")
        evidence = f"DDD roles present ({count}/4): {', '.join(roles) if roles else 'none'}"
        return score, evidence

    def _score_boundary_isolation(
        self, boundary: dict, class_by_name: dict, all_endpoints: list[dict] | None
    ) -> tuple[float, str]:
        cohesion = boundary.get("cohesion_score", 50)
        coupling = boundary.get("coupling_score", 50)
        total = cohesion + coupling
        score = cohesion / total if total > 0 else 0.5
        return round(score, 2), f"Boundary isolation score: {round(score * 100)}% (cohesion={cohesion}%, coupling={coupling}%)"

    def _score_entity_ownership(
        self, boundary: dict, class_by_name: dict, all_endpoints: list[dict] | None
    ) -> tuple[float, str]:
        classes = set(boundary.get("classes", []) or [])
        entities = [c for c in classes if class_by_name.get(c, {}).get("is_entity")]
        if entities:
            return 1.0, f"Owns domain entities: {', '.join(entities)}"
        return 0.5, "No direct domain entity owned"

    def _score_endpoint_clarity(
        self, boundary: dict, class_by_name: dict, all_endpoints: list[dict] | None
    ) -> tuple[float, str]:
        eps = boundary.get("api_endpoints", [])
        if eps:
            return 1.0, f"{len(eps)} API endpoint(s) mapped cleanly to boundary"
        classes = set(boundary.get("classes", []) or [])
        has_ctrl = any(class_by_name.get(c, {}).get("is_controller") for c in classes)
        if not has_ctrl:
            return 1.0, "Service is internal (no exposed HTTP endpoints required)"
        return 0.5, "Controller present but 0 HTTP endpoints attributed"

    def _score_package_alignment(
        self, boundary: dict, class_by_name: dict, all_endpoints: list[dict] | None
    ) -> tuple[float, str]:
        classes = boundary.get("classes", []) or []
        packages = set(class_by_name.get(c, {}).get("package", "") for c in classes if class_by_name.get(c, {}).get("package"))
        pkg_count = len(packages)
        if pkg_count <= 2:
            return 1.0, f"High package cohesion across {pkg_count} package(s)"
        elif pkg_count == 3:
            return 0.7, f"Moderate package dispersion across 3 packages"
        return 0.4, f"Classes dispersed across {pkg_count} packages"

    def _score_dependency_health(
        self, boundary: dict, class_by_name: dict, all_endpoints: list[dict] | None
    ) -> tuple[float, str]:
        classes = boundary.get("classes", []) or []
        has_cycles = any(
            bool(class_by_name.get(c, {}).get("circular_dependencies"))
            for c in classes
        )
        if not has_cycles:
            return 1.0, "No internal circular dependencies detected"
        return 0.5, "Internal circular dependencies present"

    def _score_static_completeness(
        self, boundary: dict, class_by_name: dict, all_endpoints: list[dict] | None
    ) -> tuple[float, str]:
        classes = boundary.get("classes", []) or []
        if not classes:
            return 0.0, "Boundary has 0 classes"
        parsed = sum(1 for c in classes if class_by_name.get(c, {}).get("lines_of_code", 0) > 0)
        frac = parsed / len(classes)
        return frac, f"{parsed}/{len(classes)} classes fully parsed by AST analyzer"
