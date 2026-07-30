"""Dependency resolver — topological sort and ready-stage computation."""

from __future__ import annotations

from collections import deque

from app.scheduling.cycle import CycleValidator


class DependencyResolver:
    """Resolves execution order using Kahn's topological sort algorithm.

    Provides both a full linear ordering and incremental stage-ready queries
    for use by the parallel executor.
    """

    def __init__(self, graph: dict[str, set[str]]):
        self._graph = graph
        self._in_degree: dict[str, int] = {}
        self._reverse: dict[str, set[str]] = {}
        self._compute()

    def _compute(self) -> None:
        self._in_degree = {node: 0 for node in self._graph}
        self._reverse = {node: set() for node in self._graph}
        for node, deps in self._graph.items():
            self._in_degree[node] = len(deps)
            for dep in deps:
                if dep in self._reverse:
                    self._reverse[dep].add(node)

    def topological_sort(self) -> list[str]:
        """Return a valid linear execution order via Kahn's algorithm.

        Raises ValueError if the graph contains a cycle.
        """
        queue = deque(sorted(node for node, deg in self._in_degree.items() if deg == 0))
        order: list[str] = []
        in_deg = dict(self._in_degree)

        while queue:
            node = queue.popleft()
            order.append(node)
            for dependent in sorted(self._reverse.get(node, set())):
                in_deg[dependent] -= 1
                if in_deg[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self._graph):
            cycle_result = CycleValidator.validate(self._graph)
            raise ValueError(f"Dependency cycle detected: {' -> '.join(cycle_result.cycle_path)}")

        return order

    def layers(self) -> list[list[str]]:
        """Return stages grouped by topological level (parallel execution layers).

        Layer 0: stages with in_degree == 0
        Layer N: stages whose dependencies are all in layers < N
        """
        in_deg = dict(self._in_degree)
        remaining = set(self._graph.keys())
        result: list[list[str]] = []

        while remaining:
            layer = sorted(name for name in remaining if in_deg[name] == 0)
            if not layer:
                raise ValueError("Cannot resolve layers: cycle detected")
            result.append(layer)
            for name in layer:
                remaining.discard(name)
                for dependent in self._reverse.get(name, set()):
                    if dependent in remaining:
                        in_deg[dependent] -= 1

        return result

    def ready_stages(self, completed: set[str]) -> list[str]:
        """Given a set of completed stages, return stages ready to execute.

        A stage is ready when all its dependencies are in the completed set.
        """
        ready = []
        for node, deps in self._graph.items():
            if node not in completed and deps.issubset(completed):
                ready.append(node)
        return sorted(ready)

    def are_all_done(self, completed: set[str]) -> bool:
        """Check if all stages are in the completed set."""
        return completed >= set(self._graph.keys())

    def validate_completion(self, completed: set[str]) -> list[str]:
        """Return list of stages that should have completed but didn't."""
        return sorted(set(self._graph.keys()) - completed)
