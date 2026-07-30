"""Graph Generator — produces React Flow-ready JSON for dependency, architecture, package graphs."""

from __future__ import annotations

import structlog

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext

logger = structlog.get_logger(__name__)

SEVERITY_COLORS = {"critical": "#dc2626", "high": "#ea580c", "medium": "#ca8a04", "low": "#16a34a"}
NODE_TYPE_COLORS = {
    "controller": "#3b82f6", "service": "#8b5cf6", "repository": "#10b981",
    "entity": "#f59e0b", "dto": "#6b7280", "interface": "#06b6d4",
    "configuration": "#ec4899", "exception": "#ef4444", "class": "#94a3b8",
}


class GraphGenerator(Analyzer):
    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="graph_generator", version="1.0.0", phase=AnalyzerPhase.GRAPH,
            description="Generates React Flow-ready JSON for dependency, architecture, package graphs",
            tags=["graph", "visualization", "react-flow"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return not context.graph_data.get("dependency_graph_json")

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        dep_graph = self._build_dependency_graph(context)
        arch_graph = self._build_architecture_graph(context)
        pkg_graph = self._build_package_graph(context)

        context.graph_data["dependency_graph_json"] = dep_graph
        context.graph_data["architecture_graph_json"] = arch_graph
        context.graph_data["package_graph_json"] = pkg_graph

        context.set_phase("graph")
        logger.info("graphs_generated")
        return context

    def _build_dependency_graph(self, ctx: AnalysisContext) -> dict:
        dep = ctx.dependency_graph or {}
        nodes = []
        for n in dep.get("nodes", []):
            node_type = n.get("type", "class")
            nodes.append({
                "id": n["id"], "type": "default",
                "position": {"x": 0, "y": 0},
                "data": {"label": n["id"], "type": node_type, "package": n.get("package", ""), "loc": n.get("loc", 0)},
                "style": {"background": NODE_TYPE_COLORS.get(node_type, "#94a3b8")},
            })
        edges = []
        for e in dep.get("edges", []):
            edges.append({
                "id": f"{e['source']}-{e['target']}",
                "source": e["source"], "target": e["target"],
                "type": "smoothstep",
                "animated": e.get("type") == "injection",
                "label": e.get("type", ""),
            })
        return {"nodes": nodes, "edges": edges}

    def _build_architecture_graph(self, ctx: AnalysisContext) -> dict:
        arch = ctx.architecture_style or {}
        layers = []
        detected = arch.get("detected_patterns", [])
        layer_names = ["Controllers", "Services", "Repositories", "Entities", "DTOs"]
        for i, name in enumerate(layer_names):
            layers.append({
                "id": f"layer-{i}", "type": "default",
                "position": {"x": 0, "y": i * 120},
                "data": {"label": name, "layer": name.lower()},
                "style": {"background": NODE_TYPE_COLORS.get(name.lower()[:-1] if name.endswith("s") else name.lower(), "#94a3b8"), "width": 200, "height": 60},
            })
        return {"nodes": layers, "edges": [], "metadata": {"primary_style": arch.get("primary_style", "unknown"), "detected_patterns": detected}}

    def _build_package_graph(self, ctx: AnalysisContext) -> dict:
        pkg_tree = ctx.metrics.get("package_tree", {}) if ctx.metrics else {}
        dep_graph = ctx.dependency_graph or {}
        pkg_deps = dep_graph.get("package_dependencies", {})

        nodes = []
        for i, (pkg, classes) in enumerate(pkg_tree.items()):
            nodes.append({
                "id": pkg, "type": "default",
                "position": {"x": (i % 4) * 250, "y": (i // 4) * 150},
                "data": {"label": pkg.split(".")[-1] if "." in pkg else pkg, "full_package": pkg, "class_count": len(classes)},
            })
        edges = []
        for src, targets in pkg_deps.items():
            for tgt in targets:
                edges.append({
                    "id": f"{src}-{tgt}", "source": src, "target": tgt,
                    "type": "smoothstep",
                })
        return {"nodes": nodes, "edges": edges}
