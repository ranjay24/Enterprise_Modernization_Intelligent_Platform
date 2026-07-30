"""Sprint 5 tests — DAG builder, dependency resolver, cycle detection."""

from app.artifacts.models import Artifact, ArtifactMetadata
from app.pipeline.stage import PipelineStage
from app.scheduling.cycle import CycleValidator
from app.scheduling.dag import DAGBuilder
from app.scheduling.resolver import DependencyResolver

# ─── Helpers ───

class DummyStage(PipelineStage):
    def __init__(self, stage_name: str, deps: list[str] | None = None):
        self._name = stage_name
        self._deps = deps

    @property
    def name(self):
        return self._name

    @property
    def phase(self):
        return self._name

    @property
    def depends_on(self):
        return self._deps if self._deps is not None else None

    def execute(self, context):
        return Artifact(
            content={"test": True},
            metadata=ArtifactMetadata(generator="test", artifact_type="test"),
        )


def make_stage(name, deps=None):
    return DummyStage(name, deps)


# ─── DAG Builder ───

class TestDAGBuilder:
    def test_empty_stages(self):
        dag = DAGBuilder([]).build()
        assert dag.adjacency == {}
        assert dag.get_layers() == []

    def test_single_root(self):
        stages = [make_stage("extraction", [])]
        dag = DAGBuilder(stages).build()
        assert dag.get_layers() == [["extraction"]]

    def test_linear_chain(self):
        stages = [
            make_stage("A", []),
            make_stage("B", ["A"]),
            make_stage("C", ["B"]),
        ]
        dag = DAGBuilder(stages).build()
        layers = dag.get_layers()
        assert layers == [["A"], ["B"], ["C"]]

    def test_parallel_independent(self):
        stages = [
            make_stage("A", []),
            make_stage("B", []),
            make_stage("C", ["A", "B"]),
        ]
        dag = DAGBuilder(stages).build()
        layers = dag.get_layers()
        assert ["A", "B"] in layers
        assert ["C"] in layers

    def test_full_pipeline_dag(self):
        from app.pipeline.stages.ai_adrs import AIADRStage
        from app.pipeline.stages.ai_boundaries import AIBoundariesStage
        from app.pipeline.stages.ai_cost import AICostStage
        from app.pipeline.stages.ai_explainability import AIExplainabilityStage
        from app.pipeline.stages.ai_migration import AIMigrationStage
        from app.pipeline.stages.ai_readiness import AIReadinessStage
        from app.pipeline.stages.enterprise_analysis import EnterpriseAnalysisStage
        from app.pipeline.stages.extraction import ExtractionStage
        from app.pipeline.stages.manifest import ManifestStage
        from app.pipeline.stages.report_generation import ReportGenerationStage
        from app.pipeline.stages.results_assembly import ResultsAssemblyStage
        from app.pipeline.stages.static_analysis import StaticAnalysisStage

        stages = [
            ExtractionStage(),
            StaticAnalysisStage(),
            EnterpriseAnalysisStage(),
            AIBoundariesStage(),
            AIReadinessStage(),
            AIADRStage(),
            AIMigrationStage(),
            AICostStage(),
            AIExplainabilityStage(),
            ResultsAssemblyStage(),
            ReportGenerationStage(),
            ManifestStage(),
        ]

        dag = DAGBuilder(stages).build()
        errors = dag.validate()
        assert errors == [], f"DAG validation failed: {errors}"

        layers = dag.get_layers()
        assert len(layers) > 0
        assert "extraction" in layers[0]

    def test_validate_catches_self_loop(self):
        stages = [make_stage("A", ["A"])]
        dag = DAGBuilder(stages).build()
        errors = dag.validate()
        assert len(errors) > 0
        assert any("cycle" in e.lower() or "self" in e.lower() for e in errors)

    def test_get_dependents(self):
        stages = [
            make_stage("A", []),
            make_stage("B", ["A"]),
            make_stage("C", ["A"]),
        ]
        dag = DAGBuilder(stages).build()
        dependents = dag.get_dependents("A")
        assert dependents == {"B", "C"}

    def test_get_dependents_leaf(self):
        stages = [
            make_stage("A", []),
            make_stage("B", ["A"]),
        ]
        dag = DAGBuilder(stages).build()
        assert dag.get_dependents("B") == set()

    def test_edge_count(self):
        stages = [
            make_stage("A", []),
            make_stage("B", ["A"]),
            make_stage("C", ["A"]),
        ]
        dag = DAGBuilder(stages).build()
        assert dag.edge_count == 2

    def test_node_count(self):
        stages = [make_stage("A"), make_stage("B"), make_stage("C")]
        dag = DAGBuilder(stages).build()
        assert dag.node_count == 3


# ─── Dependency Resolver ───

class TestDependencyResolver:
    def test_ready_stages_no_deps(self):
        graph = {"A": set(), "B": set()}
        resolver = DependencyResolver(graph)
        ready = resolver.ready_stages(set())
        assert set(ready) == {"A", "B"}

    def test_ready_stages_with_deps(self):
        graph = {"A": set(), "B": {"A"}, "C": {"A"}}
        resolver = DependencyResolver(graph)
        ready = resolver.ready_stages(set())
        assert ready == ["A"]

    def test_ready_stages_after_completion(self):
        graph = {"A": set(), "B": {"A"}, "C": {"A"}}
        resolver = DependencyResolver(graph)
        ready = resolver.ready_stages({"A"})
        assert set(ready) == {"B", "C"}

    def test_are_all_done(self):
        graph = {"A": set(), "B": {"A"}, "C": {"B"}}
        resolver = DependencyResolver(graph)
        assert not resolver.are_all_done(set())
        assert resolver.are_all_done({"A", "B", "C"})

    def test_topological_order_linear(self):
        graph = {"A": set(), "B": {"A"}, "C": {"B"}}
        resolver = DependencyResolver(graph)
        order = resolver.topological_sort()
        assert order.index("A") < order.index("B") < order.index("C")

    def test_topological_order_diamond(self):
        graph = {"A": set(), "B": {"A"}, "C": {"A"}, "D": {"B", "C"}}
        resolver = DependencyResolver(graph)
        order = resolver.topological_sort()
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_layers(self):
        graph = {"A": set(), "B": {"A"}, "C": {"A"}, "D": {"B", "C"}}
        resolver = DependencyResolver(graph)
        layers = resolver.layers()
        assert layers[0] == ["A"]
        assert set(layers[1]) == {"B", "C"}
        assert layers[2] == ["D"]


# ─── Cycle Detection ───

class TestCycleDetection:
    def test_no_cycle(self):
        graph = {"A": set(), "B": {"A"}, "C": {"B"}}
        result = CycleValidator.validate(graph)
        assert not result.has_cycle

    def test_direct_cycle(self):
        graph = {"A": {"B"}, "B": {"A"}}
        result = CycleValidator.validate(graph)
        assert result.has_cycle
        assert len(result.cycle_path) > 0

    def test_self_loop(self):
        graph = {"A": {"A"}}
        result = CycleValidator.validate(graph)
        assert result.has_cycle

    def test_longer_cycle(self):
        graph = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
        result = CycleValidator.validate(graph)
        assert result.has_cycle

    def test_validate_graph_no_cycle(self):
        graph = {"A": set(), "B": {"A"}, "C": {"B"}}
        errors = CycleValidator.validate_graph(graph, {"A", "B", "C"})
        assert errors == []

    def test_validate_graph_finds_cycle(self):
        graph = {"A": {"B"}, "B": {"A"}}
        errors = CycleValidator.validate_graph(graph, {"A", "B"})
        assert len(errors) > 0

    def test_validate_graph_finds_self_loop(self):
        graph = {"A": {"A"}}
        errors = CycleValidator.validate_graph(graph, {"A"})
        assert len(errors) > 0
