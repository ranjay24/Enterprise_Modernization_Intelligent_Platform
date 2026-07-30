"""Dependency Graph Analyzer — builds dependency graph, detects circular deps and coupling."""

from __future__ import annotations

import structlog

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext
from app.analysis.events.bus import EventType
from app.core.analysis_profile import get_profile_for_settings

logger = structlog.get_logger(__name__)


class DependencyGraphAnalyzer(Analyzer):
    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="dependency_graph", version="1.0.0", phase=AnalyzerPhase.DEPENDENCY,
            description="Builds dependency graph, detects circular deps and coupling",
            tags=["dependency", "graph", "circular"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return context.dependency_graph is None

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        classes = context.parsed_classes
        class_map = {c.name: c for c in classes}

        edges = []
        for c in classes:
            for dep in c.dependencies:
                if dep in class_map:
                    edge_type = "injection" if dep in c.injected_fields else "import"
                    edges.append({"source": c.name, "target": dep, "type": edge_type})

        import_cycles = self._detect_cycles(class_map, use_injections=False)
        injection_cycles = self._detect_cycles(class_map, use_injections=True)
        all_cycles = self._dedup_cycles(import_cycles + injection_cycles)

        package_deps = self._build_package_dependencies(classes)
        package_circular = self._detect_package_cycles(package_deps)

        highly_coupled = self._find_highly_coupled(classes, class_map)

        package_tree: dict[str, list[str]] = {}
        for c in classes:
            package_tree.setdefault(c.package or "default", []).append(c.name)

        graph = {
            "nodes": [{"id": c.name, "package": c.package, "type": self._node_type(c), "loc": c.lines_of_code, "methods": c.method_count} for c in classes],
            "edges": edges,
            "node_count": len(classes),
            "edge_count": len(edges),
            "circular_dependencies": all_cycles,
            "circular_count": len(all_cycles),
            "import_cycles": import_cycles,
            "injection_cycles": injection_cycles,
            "package_dependencies": package_deps,
            "package_circular_dependencies": package_circular,
            "highly_coupled": highly_coupled,
            "package_tree": package_tree,
        }

        context.dependency_graph = graph
        context.circular_dependencies = all_cycles
        context.coupling_analysis = {
            "avg_dependencies": round(sum(len(c.dependencies) for c in classes) / len(classes), 1) if classes else 0,
            "max_dependencies": max((len(c.dependencies) for c in classes), default=0),
            "highly_coupled_count": len(highly_coupled),
            "circular_cycle_count": len(all_cycles),
        }

        context.add_event(EventType.DEPENDENCIES_GENERATED.value, {
            "node_count": len(classes), "edge_count": len(edges), "circular_count": len(all_cycles),
        })
        context.set_phase("dependency")

        logger.info("dependency_graph_built", nodes=len(classes), edges=len(edges), cycles=len(all_cycles))
        return context

    def _node_type(self, c) -> str:
        if c.is_controller: return "controller"
        if c.is_service: return "service"
        if c.is_repository: return "repository"
        if c.is_entity: return "entity"
        if c.is_dto: return "dto"
        if c.is_configuration: return "configuration"
        if c.is_interface: return "interface"
        if c.is_exception: return "exception"
        return "class"

    def _detect_cycles(self, class_map: dict, use_injections: bool) -> list[dict]:
        seen = set()
        result = []

        def dfs(name, path, visiting):
            if name in visiting:
                idx = path.index(name)
                cycle = path[idx:] + [name]
                canonical = tuple(sorted(set(cycle)))
                if canonical not in seen:
                    seen.add(canonical)
                    result.append({"cycle": cycle, "type": "injection" if use_injections else "import"})
                return
            if name in path:
                return
            path.append(name)
            visiting.add(name)
            c = class_map.get(name)
            if c:
                deps = c.injected_fields if use_injections else [d for d in c.dependencies if d not in c.injected_fields]
                for dep in deps:
                    if dep in class_map:
                        dfs(dep, path, visiting)
            path.pop()
            visiting.remove(name)

        for c in class_map.values():
            dfs(c.name, [], set())
        return result

    def _dedup_cycles(self, cycles: list[dict]) -> list[dict]:
        seen = set()
        result = []
        for cycle in cycles:
            key = tuple(sorted(set(cycle["cycle"])))
            if key not in seen:
                seen.add(key)
                result.append(cycle)
        return result

    def _build_package_dependencies(self, classes) -> dict[str, set[str]]:
        pkg_deps: dict[str, set[str]] = {}
        for c in classes:
            src_pkg = c.package or "default"
            for dep_name in c.dependencies:
                for c2 in classes:
                    if c2.name == dep_name and c2.package != src_pkg:
                        pkg_deps.setdefault(src_pkg, set()).add(c2.package or "default")
        return {k: list(v) for k, v in pkg_deps.items()}

    def _detect_package_cycles(self, pkg_deps: dict[str, list[str]]) -> list[dict]:
        seen = set()
        result = []
        all_pkgs = set(pkg_deps.keys())
        for deps in pkg_deps.values():
            all_pkgs.update(deps)

        def dfs(pkg, path, visiting):
            if pkg in visiting:
                idx = path.index(pkg)
                cycle = path[idx:] + [pkg]
                canonical = tuple(sorted(set(cycle)))
                if canonical not in seen:
                    seen.add(canonical)
                    result.append({"cycle": cycle, "type": "package"})
                return
            if pkg in path:
                return
            path.append(pkg)
            visiting.add(pkg)
            for dep in pkg_deps.get(pkg, []):
                dfs(dep, path, visiting)
            path.pop()
            visiting.remove(pkg)

        for pkg in all_pkgs:
            dfs(pkg, [], set())
        return result

    def _find_highly_coupled(self, classes, class_map: dict) -> list[dict]:
        coupled = []
        for c in classes:
            dep_count = len(c.dependencies)
            inj_count = len(c.injected_fields)
            if dep_count > 10 or inj_count > 5:
                coupled.append({
                    "name": c.name, "package": c.package,
                    "dependency_count": dep_count, "injection_count": inj_count,
                    "coupling_score": min(100, dep_count * 5 + inj_count * 10),
                })
        profile = get_profile_for_settings()
        return sorted(coupled, key=lambda x: x["coupling_score"], reverse=True)[:profile.graph_max_highly_coupled]
