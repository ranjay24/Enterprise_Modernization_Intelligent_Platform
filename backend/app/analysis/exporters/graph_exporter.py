"""Graph Exporter — exports graph data in React Flow format."""

from __future__ import annotations

import json


class GraphExporter:
    def export_dependency_graph(self, graph_data: dict) -> str:
        return json.dumps(graph_data.get("dependency_graph_json", {}), indent=2, default=str)

    def export_architecture_graph(self, graph_data: dict) -> str:
        return json.dumps(graph_data.get("architecture_graph_json", {}), indent=2, default=str)

    def export_package_graph(self, graph_data: dict) -> str:
        return json.dumps(graph_data.get("package_graph_json", {}), indent=2, default=str)

    def export_all(self, graph_data: dict) -> dict[str, str]:
        return {
            "dependency": self.export_dependency_graph(graph_data),
            "architecture": self.export_architecture_graph(graph_data),
            "package": self.export_package_graph(graph_data),
        }
