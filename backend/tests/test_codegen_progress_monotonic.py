"""Guard: codegen progress is monotonic — it never decreases, and reaches 100.

Regression for the Modernization Studio bug where the hero progress bar
oscillated (80 -> 50 -> 30..70 -> 80 ...) because the orchestrator overwrote
progress with absolute per-iteration values during the review -> replan ->
regenerate loop.
"""

from types import SimpleNamespace

import pytest

from app.agents.architecture import ArchitectureDesignerAgent
from app.agents.planner import ServicePlannerAgent
from app.agents.reviewer import ReviewAgent
from app.codegen import models as codegen_models
from app.codegen.orchestrator import CodeGenOrchestrator
from app.codegen.project_builder import build_scaffold_service


@pytest.fixture
def boundaries():
    return [
        {
            "name": "OrderService",
            "business_capability": "Order Management",
            "classes": ["OrderController", "OrderService"],
            "api_endpoints": [{"method": "POST", "path": "/orders"}],
        },
        {
            "name": "InventoryService",
            "business_capability": "Inventory",
            "classes": ["InventoryController", "InventoryService"],
            "api_endpoints": [{"method": "GET", "path": "/inventory"}],
        },
    ]


class TestMonotonicReport:
    def test_report_never_decreases_within_a_run(self):
        milestones = []
        orch = CodeGenOrchestrator(progress_callback=lambda _j, p, s: milestones.append(p))

        orch._report("job-1", 5, "architecture_design")
        orch._report("job-1", 15, "service_planning")
        orch._report("job-1", 30, "code_generation")
        orch._report("job-1", 55, "code_generation_order-service")
        orch._report("job-1", 80, "review")
        # Replan restarts from a lower absolute value — must stay clamped at 80.
        orch._report("job-1", 50, "service_planning")
        orch._report("job-1", 30, "code_generation")
        orch._report("job-1", 80, "review")
        orch._report("job-1", 100, "finalize")

        assert milestones == [5, 15, 30, 55, 80, 80, 80, 80, 100]
        assert all(a <= b for a, b in zip(milestones, milestones[1:]))

    def test_report_tracks_absolute_high_water_mark(self):
        milestones = []
        orch = CodeGenOrchestrator(progress_callback=lambda _j, p, s: milestones.append(p))
        for value in (20, 40, 35, 45, 10, 90):
            orch._report("job-1", value, "code_generation")
        assert milestones == [20, 40, 40, 45, 45, 90]


class TestOrchestratorProgressMonotonic:
    def test_full_loop_progress_is_non_decreasing_and_ends_at_100(self, monkeypatch, boundaries):
        from app.codegen import orchestrator as orch

        milestones: list[tuple[int, str]] = []

        class FakeDesigner:
            name = "architecture_designer"
            agent_id = "architecture_designer"
            output_artifact = "architecture_design"

            def run(self, analysis_data, boundaries, waves, cost, job_id=""):
                design = ArchitectureDesignerAgent().fallback_design(boundaries, {})
                return design, {"model_id": "fake-nova"}, True

        class FakePlanner:
            name = "service_planner"
            agent_id = "service_planner"
            output_artifact = "codegen_plan"

            def run(self, architecture, boundaries, analysis_data, review_feedback=None, job_id=""):
                return ServicePlannerAgent().fallback_plan(architecture, boundaries), {"model_id": "fake-nova"}, True

        class FakeGenerator:
            name = "code_generation"
            agent_id = "code_generation"
            output_artifact = "service_code"

            def run(self, service_plan, source_boundary, analysis_data, regeneration_context=None, job_id=""):
                code = build_scaffold_service(service_plan)
                code["service_id"] = codegen_models.normalize_service_id(service_plan, "service")
                if regeneration_context is None:
                    # First round is deficient -> reviewer rejects -> replan.
                    code["files"] = [f for f in code["files"] if "/repository/" not in f["path"]]
                return code, {"model_id": "fake-nova"}, True

        class FakeReviewer:
            name = "review"
            agent_id = "review"
            output_artifact = "review_report"

            def run(self, services_code, plan, architecture, iteration, job_id=""):
                report = ReviewAgent().fallback_review(services_code)
                report["iteration"] = iteration
                return report, {"model_id": "fake-nova"}, True

        class FakeJobRepo:
            def update_job(self, **kwargs):
                return None

        class FakeArtifactRepo:
            def __init__(self, boundaries):
                self.store = {
                    ("job-1", "results_assembly"): {
                        "content": {"service_boundaries": boundaries}
                    }
                }

            def load(self, job_id, name):
                entry = self.store.get((job_id, name))
                if entry is None:
                    return None
                return SimpleNamespace(content=entry["content"])

            def load_content(self, job_id, name):
                entry = self.store.get((job_id, name))
                return entry["content"] if entry else None

            def create_artifact(self, job_id, stage_name, content, generator, model_id, is_degraded=False):
                return {"artifact_id": f"{job_id}-{stage_name}"}

            def save(self, job_id, stage_name, artifact):
                self.store[(job_id, stage_name)] = {"content": artifact.get("content", {})}

            def artifact_exists(self, job_id, name):
                return (job_id, name) in self.store

        monkeypatch.setattr(orch, "ArchitectureDesignerAgent", FakeDesigner)
        monkeypatch.setattr(orch, "ServicePlannerAgent", FakePlanner)
        monkeypatch.setattr(orch, "CodeGenerationAgent", FakeGenerator)
        monkeypatch.setattr(orch, "ReviewAgent", FakeReviewer)
        monkeypatch.setattr(orch, "JobRepository", FakeJobRepo)

        repo = FakeArtifactRepo(boundaries)
        orchestrator = orch.CodeGenOrchestrator(
            artifact_repo=repo,
            progress_callback=lambda job_id, p, s: milestones.append((p, s)),
        )
        summary = orchestrator.run("job-1", max_iterations=3)

        assert summary["approved"] is True
        assert summary["status"] == "generation_complete"

        progress_values = [p for p, _ in milestones]
        assert all(a <= b for a, b in zip(progress_values, progress_values[1:]))
        assert progress_values[-1] == 100
        # The final milestone must be reported as the "finalize" stage.
        assert milestones[-1] == (100, "finalize")
