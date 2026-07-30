"""Quality Metrics — maintainability, complexity, technical debt estimation."""

from __future__ import annotations

import structlog

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext

logger = structlog.get_logger(__name__)


class QualityMetricsAnalyzer(Analyzer):
    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="quality_metrics", version="1.0.0", phase=AnalyzerPhase.METRICS,
            description="Calculates maintainability, complexity, and debt estimates",
            tags=["metrics", "quality", "debt"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return "maintainability_score" not in context.quality_metrics

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        metrics = context.metrics
        classes = context.parsed_classes

        god_class_count = len(metrics.get("god_classes", []))
        total_classes = metrics.get("total_classes", 1)
        god_ratio = god_class_count / total_classes if total_classes > 0 else 0

        avg_complexity = metrics.get("avg_cyclomatic_complexity", 0)
        total_loc = metrics.get("total_lines", 0)
        avg_class_size = metrics.get("avg_class_size", 0)

        maintainability = max(0, 100 - (god_ratio * 100) - (avg_complexity * 2) - (avg_class_size / 20))

        complexity_score = max(0, 100 - (avg_complexity * 5) - (god_class_count * 10))

        debt_hours = god_class_count * 8 + len(metrics.get("long_methods", [])) * 2 + (total_loc / 10000) * 5
        debt_ratio = min(100, debt_hours / (total_loc / 100 + 1) * 10)

        injection_count = sum(len(c.injected_fields) for c in classes)
        avg_injection = injection_count / total_classes if total_classes > 0 else 0
        cohesion_estimate = max(0, 100 - (avg_injection * 10) - (god_ratio * 50))

        duplication = self._estimate_duplication(classes)

        quality_metrics = {
            "maintainability_score": round(maintainability, 1),
            "complexity_score": round(complexity_score, 1),
            "technical_debt_hours": round(debt_hours, 1),
            "debt_ratio": round(debt_ratio, 1),
            "cohesion_estimate": round(cohesion_estimate, 1),
            "coupling_estimate": round(min(100, avg_injection * 15 + god_ratio * 40), 1),
            "duplication_percent": round(duplication, 1),
            "overall_quality": round((maintainability + complexity_score + cohesion_estimate) / 3, 1),
        }

        context.quality_metrics = quality_metrics
        context.set_phase("quality_metrics")

        logger.info("quality_calculated", maintainability=round(maintainability, 1))
        return context

    def _estimate_duplication(self, classes) -> float:
        if not classes:
            return 0.0
        seen_bodies: dict[str, int] = {}
        dup_lines = 0
        total_lines = 0
        for c in classes:
            if not c.method_lines:
                continue
            for i, m in enumerate(c.method_lines):
                start = m["start_line"]
                end = c.method_lines[i + 1]["start_line"] if i + 1 < len(c.method_lines) else c.lines_of_code
                body_len = end - start
                total_lines += body_len
                if body_len >= 5:
                    key = f"{c.name}:{start}"
                    if key in seen_bodies:
                        dup_lines += body_len
                    else:
                        seen_bodies[key] = body_len
        return (dup_lines / total_lines * 100) if total_lines > 0 else 0.0
