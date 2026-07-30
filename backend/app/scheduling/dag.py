"""DAG builder — constructs dependency graph from pipeline stages."""

from __future__ import annotations

import structlog

from app.pipeline.stage import PipelineStage
from app.scheduling.cycle import CycleValidator

logger = structlog.get_logger(__name__)


class StageNode:
    """A node in the dependency DAG."""

    __slots__ = ("depends_on", "name", "stage")

    def __init__(self, name: str, depends_on: list[str], stage: PipelineStage):
        self.name = name
        self.depends_on = depends_on
        self.stage = stage

    def __repr__(self) -> str:
        return f"StageNode({self.name!r}, deps={self.depends_on})"


class DAGBuilder:
    """Builds a directed acyclic graph from pipeline stages.

    Each stage declares its dependencies via the ``depends_on`` property.
    The builder validates the graph before exposing it.
    """

    def __init__(self, stages: list[PipelineStage]):
        self._stages = list(stages)
        self._nodes: dict[str, StageNode] = {}
        self._adjacency: dict[str, set[str]] = {}
        self._built = False

    def build(self) -> DAGBuilder:
        """Build the graph from stages. Must be called before any other method."""
        self._nodes.clear()
        self._adjacency.clear()

        for stage in self._stages:
            name = stage.name
            deps = stage.depends_on or []
            self._nodes[name] = StageNode(name=name, depends_on=deps, stage=stage)
            self._adjacency[name] = set(deps)

        self._built = True
        logger.info("dag_built", stages=len(self._nodes), edges=sum(len(d) for d in self._adjacency.values()))
        return self

    def validate(self) -> list[str]:
        """Validate the graph. Returns list of error strings (empty = valid)."""
        self._ensure_built()
        all_names = set(self._nodes.keys())
        return CycleValidator.validate_graph(self._adjacency, all_names)

    def get_layers(self) -> list[list[str]]:
        """Return stages grouped into parallel execution layers.

        Layer 0 has no dependencies. Layer N depends only on layers < N.
        Stages within the same layer can execute concurrently.
        """
        self._ensure_built()
        in_degree: dict[str, int] = {name: 0 for name in self._adjacency}
        for name, deps in self._adjacency.items():
            in_degree[name] = len(deps)

        layers: list[list[str]] = []
        remaining = set(self._adjacency.keys())

        while remaining:
            layer = sorted(name for name in remaining if in_degree[name] == 0)
            if not layer:
                break
            layers.append(layer)
            for name in layer:
                remaining.discard(name)
                for other in remaining:
                    if name in self._adjacency[other]:
                        in_degree[other] -= 1

        return layers

    def get_dependents(self, stage_name: str) -> set[str]:
        """Return all stages that directly depend on the given stage."""
        self._ensure_built()
        dependents = set()
        for name, deps in self._adjacency.items():
            if stage_name in deps:
                dependents.add(name)
        return dependents

    def get_all_dependents(self, stage_name: str) -> set[str]:
        """Return all transitive dependents of a stage (BFS)."""
        self._ensure_built()
        visited: set[str] = set()
        queue = [stage_name]
        while queue:
            current = queue.pop(0)
            for dep in self.get_dependents(current):
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
        visited.discard(stage_name)
        return visited

    def get_node(self, name: str) -> StageNode | None:
        self._ensure_built()
        return self._nodes.get(name)

    @property
    def adjacency(self) -> dict[str, set[str]]:
        self._ensure_built()
        return dict(self._adjacency)

    @property
    def stage_names(self) -> list[str]:
        self._ensure_built()
        return list(self._nodes.keys())

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        self._ensure_built()
        return sum(len(d) for d in self._adjacency.values())

    def _ensure_built(self) -> None:
        if not self._built:
            raise RuntimeError("DAG not built. Call build() first.")
