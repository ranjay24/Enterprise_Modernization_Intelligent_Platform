"""Tests for the Phase 3 agentic code generation modules."""

import pytest

from app.agents import get_agent_registry
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


class TestAgentRegistry:
    def test_all_agents_registered(self):
        registry = get_agent_registry()
        ids = {a.agent_id for a in registry.all()}
        assert {"architecture_designer", "service_planner", "code_generation", "review"} <= ids

    def test_definitions_load(self):
        registry = get_agent_registry()
        for agent in registry.all():
            definition = agent.definition()
            assert definition.definition_file.endswith(".md")
            assert definition.content, f"definition empty for {agent.agent_id}"


class TestArchitectureDesigner:
    def test_fallback_design_has_gateway_and_services(self, boundaries):
        agent = ArchitectureDesignerAgent()
        design = agent.fallback_design(boundaries, {})
        node_types = {n["type"] for n in design["nodes"]}
        assert "gateway" in node_types
        assert "service" in node_types
        assert len(design["services"]) == len(boundaries)
        for svc in design["services"]:
            assert svc["broker_role"] in codegen_models.VALID_BROKER_ROLES
            assert svc["resilience"]

    def test_fallback_respects_missing_analysis(self):
        agent = ArchitectureDesignerAgent()
        design = agent.fallback_design([], {})
        assert design["nodes"]


class TestServicePlanner:
    def test_fallback_plan_waves_and_services(self, boundaries):
        agent = ServicePlannerAgent()
        design = ArchitectureDesignerAgent().fallback_design(boundaries, {})
        plan = agent.fallback_plan(design, boundaries)
        assert plan["waves"]
        service_plans = codegen_models.normalize_service_list(plan)
        assert len(service_plans) == len(boundaries)
        for svc in service_plans:
            assert codegen_models.normalize_service_id(svc)
            assert svc["package"].startswith("com.emip")


class TestReview:
    def test_fallback_review_flags_missing_files(self):
        agent = ReviewAgent()
        code = {"service_id": "order-service", "files": []}
        report = agent.fallback_review([code])
        assert report["approved"] is False
        severities = {f["severity"] for f in report["findings"]}
        assert "critical" in severities


class TestModels:
    def test_normalize_service_code_dedupes_files(self):
        code = {
            "service_id": "order-service",
            "files": [
                {"path": "pom.xml", "content": "x"},
                {"path": "pom.xml", "content": "y"},
                {"path": "app.yml", "content": "z"},
            ],
        }
        normalized = codegen_models.normalize_service_code(code)
        assert len(normalized["files"]) == 2

    def test_blocking_findings(self):
        report = {
            "approved": False,
            "findings": [
                {"severity": "critical", "file": "a", "finding": "f1", "recommendation": "r1"},
                {"severity": "minor", "file": "b", "finding": "f2", "recommendation": "r2"},
            ],
        }
        blocking = codegen_models.blocking_findings(report)
        assert len(blocking) == 1
        assert blocking[0]["severity"] == "critical"
        assert codegen_models.is_approved(report) is False


class TestScaffoldBuilder:
    @pytest.mark.parametrize(
        "broker_role,expect_kafka,expect_rabbit",
        [
            ("kafka", True, False),
            ("rabbitmq", False, True),
            ("both", True, True),
            ("none", False, False),
        ],
    )
    def test_broker_messaging(self, broker_role, expect_kafka, expect_rabbit):
        plan = {
            "id": "order-service",
            "package": "com.emip.order",
            "broker_role": broker_role,
            "events": {"publishes": [{"topic": "OrderCreated"}], "subscribes": [{"queue": "email"}]},
        }
        code = build_scaffold_service(plan)
        messaging_files = [f for f in code["files"] if "messaging" in f["path"]]
        content = "\n".join(f["content"] for f in messaging_files)
        assert ("@KafkaListener" in content) == expect_kafka
        assert ("@RabbitListener" in content) == expect_rabbit
        assert bool(messaging_files) == (expect_kafka or expect_rabbit)

    def test_scaffold_has_core_files(self):
        plan = {"id": "user-service", "package": "com.emip.user", "broker_role": "none"}
        code = build_scaffold_service(plan)
        paths = [f["path"] for f in code["files"]]
        for required in ["pom.xml", "application.yml", "resilience4j.yml", "Dockerfile", "openapi.yaml"]:
            assert any(p.endswith(required) for p in paths), f"missing {required}"
        assert any(p.endswith("Application.java") for p in paths)
        assert any(p.endswith("Controller.java") for p in paths)
        assert any(p.endswith("SmokeTest.java") for p in paths)

    def test_scaffold_respects_resilience_tuning(self):
        plan = {
            "id": "order-service",
            "package": "com.emip.order",
            "broker_role": "none",
            "resilience": {"retry": {"max_attempts": 7, "backoff_ms": 200}},
        }
        code = build_scaffold_service(plan)
        resilience = next(f for f in code["files"] if f["path"].endswith("resilience4j.yml"))
        assert "maxAttempts: 7" in resilience["content"]
        assert "waitDuration: 200ms" in resilience["content"]

    def test_scaffold_class_names_are_valid(self):
        plan = {"id": "order-service", "package": "com.emip.order", "broker_role": "none"}
        code = build_scaffold_service(plan)
        app_file = next(f for f in code["files"] if f["path"].endswith("OrderServiceApplication.java"))
        assert "OrderServiceApplication" in app_file["content"]
        assert "package com.emip.order;" in app_file["content"]
