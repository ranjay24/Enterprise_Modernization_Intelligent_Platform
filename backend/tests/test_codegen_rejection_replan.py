"""P2.3 — prove the codegen review → replan → regenerate loop.

Guards: the fallback reviewer must genuinely reject deficient code (not just
approve any output that contains .java files), and the orchestrator must map
findings back to the affected service, pass them to the planner as feedback,
and regenerate until approval or max iterations.
"""

from types import SimpleNamespace

import pytest

from app.agents.architecture import ArchitectureDesignerAgent
from app.agents.planner import ServicePlannerAgent
from app.agents.reviewer import ReviewAgent
from app.codegen import models as codegen_models
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


def _service_code(service_id: str = "order-service", with_repository: bool = True) -> dict:
    code = build_scaffold_service({
        "id": service_id,
        "package": "com.emip.orderservice",
        "server_port": 8081,
        "broker_role": "none",
    })
    code["service_id"] = service_id
    if not with_repository:
        code["files"] = [f for f in code["files"] if "/repository/" not in f["path"]]
    return code


class TestFallbackReview:
    def test_approves_well_formed_scaffold(self):
        report = ReviewAgent().fallback_review([_service_code()])
        assert report["approved"] is True
        severities = {f["severity"] for f in report["findings"]}
        assert "critical" not in severities and "major" not in severities

    def test_rejects_missing_repository_layer(self):
        report = ReviewAgent().fallback_review([_service_code(with_repository=False)])
        assert report["approved"] is False
        blockers = codegen_models.blocking_findings(report)
        assert any(f["id"] == "order-service-no-repository" for f in blockers)
        assert blockers[0]["severity"] == "major"

    def test_major_finding_blocks_approval(self):
        report = {
            "approved": False,
            "findings": [
                {"severity": "major", "file": "a", "finding": "f1", "recommendation": "r1"},
            ],
        }
        assert codegen_models.is_approved(report) is False
        assert len(codegen_models.blocking_findings(report)) == 1


class TestFindingMapping:
    def test_affected_service_ids_matches_package_and_id(self):
        from app.codegen.orchestrator import CodeGenOrchestrator

        plan = {
            "services": [
                {"id": "order-service", "package": "com.emip.orderservice"},
                {"id": "inventory-service", "package": "com.emip.inventoryservice"},
            ]
        }
        findings = [
            {"severity": "major", "file": "src/main/java/com/emip/orderservice/repository"},
            {"severity": "major", "file": "src/main/java/com/emip/inventoryservice/web"},
        ]
        affected = CodeGenOrchestrator()._affected_service_ids(findings, plan)
        assert affected == {"order-service", "inventory-service"}


class TestOrchestratorReplan:
    """End-to-end: reject on iteration 1, replan with feedback, approve on iteration 2."""

    def test_rejection_forces_replan_and_regeneration(self, monkeypatch, boundaries):
        from app.codegen import orchestrator as orch

        planner_feedback: list = []
        generator_calls: list = []

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
                planner_feedback.append(review_feedback)
                plan = ServicePlannerAgent().fallback_plan(architecture, boundaries)
                if review_feedback:
                    plan["regeneration_notes"] = [f.get("finding") for f in review_feedback]
                return plan, {"model_id": "fake-nova"}, True

        class FakeGenerator:
            name = "code_generation"
            agent_id = "code_generation"
            output_artifact = "service_code"

            def run(self, service_plan, source_boundary, analysis_data, regeneration_context=None, job_id=""):
                generator_calls.append(bool(regeneration_context))
                code = build_scaffold_service(service_plan)
                code["service_id"] = codegen_models.normalize_service_id(service_plan, "service")
                if regeneration_context is None:
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
        orchestrator = orch.CodeGenOrchestrator(artifact_repo=repo)
        summary = orchestrator.run("job-1", max_iterations=3)

        assert summary["approved"] is True
        assert summary["status"] == "generation_complete"
        assert summary["iterations"] == 2

        # Planner was called once without feedback and once WITH rejection feedback.
        assert len(planner_feedback) == 2
        assert planner_feedback[0] is None
        assert planner_feedback[1] and len(planner_feedback[1]) >= 1

        # Every service was regenerated with regeneration context on round 2.
        assert len(generator_calls) == len(boundaries) * 2
        assert generator_calls[: len(boundaries)] == [False] * len(boundaries)
        assert generator_calls[len(boundaries):] == [True] * len(boundaries)

        # The codegen_summary artifact was persisted.
        assert repo.load_content("job-1", "codegen_summary") is not None

    def test_max_iterations_exhausted_without_approval(self, monkeypatch, boundaries):
        """If regeneration never fixes the problem, the loop stops at max iterations."""
        from app.codegen import orchestrator as orch

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
                plan = ServicePlannerAgent().fallback_plan(architecture, boundaries)
                return plan, {"model_id": "fake-nova"}, True

        class FakeGenerator:
            name = "code_generation"
            agent_id = "code_generation"
            output_artifact = "service_code"

            def run(self, service_plan, source_boundary, analysis_data, regeneration_context=None, job_id=""):
                code = build_scaffold_service(service_plan)
                code["service_id"] = codegen_models.normalize_service_id(service_plan, "service")
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

        orchestrator = orch.CodeGenOrchestrator(artifact_repo=FakeArtifactRepo(boundaries))
        summary = orchestrator.run("job-1", max_iterations=3)

        assert summary["approved"] is False
        assert summary["status"] == "generation_with_warnings"
        assert summary["iterations"] == 3
