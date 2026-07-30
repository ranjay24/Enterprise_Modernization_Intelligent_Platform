"""Cycle validator — detects dependency cycles in the stage DAG."""

from __future__ import annotations

from enum import Enum


class CycleDetectionResult:
    """Result of cycle detection."""

    __slots__ = ("has_cycle", "cycle_path", "cycle_nodes")

    def __init__(self, has_cycle: bool, cycle_path: list[str] | None = None, cycle_nodes: set[str] | None = None):
        self.has_cycle = has_cycle
        self.cycle_path = cycle_path or []
        self.cycle_nodes = cycle_nodes or set()

    def __bool__(self) -> bool:
        return self.has_cycle


class CycleValidator:
    """Validates that a dependency graph is a DAG (no cycles).

    Uses DFS-based cycle detection with path tracking for diagnostics.
    """

    @staticmethod
    def validate(graph: dict[str, set[str]]) -> CycleDetectionResult:
        """Detect cycles using iterative DFS.

        Args:
            graph: Adjacency list mapping stage_name -> set of dependency names.

        Returns:
            CycleDetectionResult with has_cycle=True and cycle_path if a cycle exists.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {node: WHITE for node in graph}
        parent: dict[str, str | None] = {node: None for node in graph}

        for node in graph:
            if color[node] != WHITE:
                continue

            stack: list[tuple[str, bool]] = [(node, False)]
            while stack:
                v, processed = stack.pop()
                if processed:
                    color[v] = BLACK
                    continue

                if color[v] == GRAY:
                    color[v] = BLACK
                    continue

                color[v] = GRAY
                stack.append((v, True))

                for neighbor in graph.get(v, set()):
                    if neighbor not in color:
                        continue
                    if color[neighbor] == GRAY:
                        path = CycleValidator._reconstruct_cycle(parent, v, neighbor)
                        return CycleDetectionResult(True, path, set(path))
                    if color[neighbor] == WHITE:
                        parent[neighbor] = v
                        stack.append((neighbor, False))

        return CycleDetectionResult(False)

    @staticmethod
    def _reconstruct_cycle(parent: dict[str, str | None], from_node: str, to_node: str) -> list[str]:
        """Reconstruct the cycle path from the DFS parent pointers."""
        path: list[str] = [to_node, from_node]
        node: str | None = from_node
        while node != to_node:
            node = parent.get(node)
            if node is None:
                break
            path.append(node)
        path.reverse()
        return path

    @staticmethod
    def validate_graph(
        graph: dict[str, set[str]],
        all_stages: set[str],
    ) -> list[str]:
        """Run all graph validation checks. Returns list of error messages (empty = valid)."""
        errors: list[str] = []

        # Check for self-dependencies
        for node, deps in graph.items():
            if node in deps:
                errors.append(f"Self-dependency detected: '{node}' depends on itself")

        # Check for missing dependencies
        for node, deps in graph.items():
            for dep in deps:
                if dep not in all_stages:
                    errors.append(f"Missing dependency: '{node}' depends on '{dep}' which is not a stage")

        # Check for unreachable stages (stages with no path from root)
        roots = all_stages - set().union(*graph.values()) if graph else all_stages
        if not roots and all_stages:
            errors.append("No root stages found (all stages have dependencies)")

        # Check for cycles
        cycle_result = CycleValidator.validate(graph)
        if cycle_result:
            errors.append(f"Dependency cycle detected: {' -> '.join(cycle_result.cycle_path)}")

        return errors
