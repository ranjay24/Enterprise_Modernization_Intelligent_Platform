"""Code Metrics Analyzer — calculates LOC, class sizes, method counts, complexity."""

from __future__ import annotations

import structlog

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext
from app.analysis.events.bus import EventType
from app.core.analysis_profile import get_profile_for_settings

logger = structlog.get_logger(__name__)


class CodeMetricsAnalyzer(Analyzer):
    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="code_metrics", version="1.0.0", phase=AnalyzerPhase.METRICS,
            description="Calculates LOC, class sizes, method counts, cyclomatic complexity",
            tags=["metrics", "quality"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return "code_metrics" not in context.metrics

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        classes = context.parsed_classes
        interfaces = context.parsed_interfaces
        all_types = classes + interfaces + context.parsed_enums

        total_loc = sum(c.lines_of_code for c in all_types)
        total_methods = sum(c.method_count for c in all_types)

        class_sizes = sorted([c.lines_of_code for c in classes], reverse=True)
        avg_class_size = round(sum(class_sizes) / len(class_sizes), 1) if class_sizes else 0
        profile = get_profile_for_settings()
        largest_classes = [{"name": c.name, "loc": c.lines_of_code, "methods": c.method_count} for c in sorted(classes, key=lambda x: x.lines_of_code, reverse=True)[:profile.metrics_max_largest_classes]]

        god_classes = [c.to_dict() for c in classes if self._is_god_class(c)]
        long_methods = self._find_long_methods(classes)

        all_complexities = []
        for c in classes:
            if not c.method_lines:
                continue
            for i, m in enumerate(c.method_lines):
                start = m["start_line"]
                end = c.method_lines[i + 1]["start_line"] if i + 1 < len(c.method_lines) else c.lines_of_code
                all_complexities.append(end - start)
        avg_complexity = round(sum(all_complexities) / len(all_complexities), 1) if all_complexities else 0

        pkg_tree: dict[str, list[str]] = {}
        for c in all_types:
            pkg_tree.setdefault(c.package or "default", []).append(c.name)

        endpoint_count = len(context.endpoints)
        controller_count = sum(1 for c in classes if c.is_controller)
        service_count = sum(1 for c in classes if c.is_service)
        repository_count = sum(1 for c in classes if c.is_repository)
        entity_count = sum(1 for c in classes if c.is_entity)
        dto_count = sum(1 for c in classes if c.is_dto)
        config_count = sum(1 for c in classes if c.is_configuration)
        exception_count = sum(1 for c in classes if c.is_exception)
        utility_count = sum(1 for c in classes if c.is_utility)

        metrics = {
            "total_files": len(all_types),
            "total_lines": total_loc,
            "total_classes": len(classes),
            "total_interfaces": len(interfaces),
            "total_enums": len(context.parsed_enums),
            "total_methods": total_methods,
            "total_endpoints": endpoint_count,
            "package_count": len(pkg_tree),
            "module_count": len(context.project_metadata.get("modules", [])) if context.project_metadata else 0,
            "avg_class_size": avg_class_size,
            "largest_classes": largest_classes,
            "god_classes": god_classes,
            "long_methods": long_methods,
            "avg_cyclomatic_complexity": avg_complexity,
            "class_type_counts": {
                "controllers": controller_count, "services": service_count,
                "repositories": repository_count, "entities": entity_count,
                "dtos": dto_count, "configurations": config_count,
                "exceptions": exception_count, "utilities": utility_count,
            },
            "public_api_count": sum(1 for c in classes if c.is_controller or c.is_service),
            "code_metrics": {
                "total_loc": total_loc, "total_methods": total_methods,
                "avg_method_length": round(total_loc / total_methods, 1) if total_methods > 0 else 0,
                "classes_over_500_loc": len([c for c in classes if c.lines_of_code > 500]),
                "classes_over_1000_loc": len([c for c in classes if c.lines_of_code > 1000]),
            },
        }

        context.metrics = metrics
        context.add_event(EventType.METRICS_CALCULATED.value, {"total_loc": total_loc, "total_classes": len(classes)})
        context.set_phase("metrics")

        logger.info("metrics_calculated", total_loc=total_loc, total_classes=len(classes), god_classes=len(god_classes))
        return context

    def _is_god_class(self, c) -> bool:
        if c.is_dto or c.is_interface or c.is_abstract:
            return False
        if len(c.injected_fields) > 5 or c.lines_of_code > 500:
            return True
        if c.lines_of_code > 300 and c.method_count > 10 and c.injected_fields:
            return True
        return False

    def _find_long_methods(self, classes) -> list[dict]:
        long = []
        for c in classes:
            if not c.method_lines:
                continue
            for i, m in enumerate(c.method_lines):
                start = m["start_line"]
                end = c.method_lines[i + 1]["start_line"] if i + 1 < len(c.method_lines) else c.lines_of_code
                length = end - start
                if length > 30:
                    long.append({"class": c.name, "method": m["name"], "line": start, "length": length})
        profile = get_profile_for_settings()
        return sorted(long, key=lambda x: x["length"], reverse=True)[:profile.metrics_max_long_methods]
