"""Tests for the Phase 3 agentic code generation modules."""

import re

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


class TestCodegenPrompts:
    """Codegen agents must resolve their prompt_id through PromptLoader.

    Guards P2.1: the four codegen prompt templates live in app/prompts/codegen/
    and must render with the variables each agent declares.
    """

    def test_every_codegen_agent_prompt_resolves_and_renders(self):
        from app.prompts.templates.loader import PromptLoader
        from app.prompts.templates.renderer import PromptRenderer

        from app.agents.generator import CodeGenerationAgent

        loader = PromptLoader()
        renderer = PromptRenderer()
        agents = [
            ArchitectureDesignerAgent(),
            ServicePlannerAgent(),
            CodeGenerationAgent(),
            ReviewAgent(),
        ]
        for agent in agents:
            prompt_id = agent.prompt_id
            assert prompt_id.startswith("codegen/"), f"unexpected prompt_id: {prompt_id}"
            template = loader.load(prompt_id)
            assert template is not None, f"prompt not resolvable: {prompt_id}"
            assert template.model_id, f"prompt has no model header: {prompt_id}"
            variables = {name: "{}" for name in template.variables}
            rendered, err = renderer.render_safe(prompt_id, variables)
            assert err == "", f"render failed for {prompt_id}: {err!r}"
            assert "[MISSING:" not in rendered, f"unresolved variable in {prompt_id}"

    def test_code_generator_file_prompt_resolves_and_renders(self):
        from app.prompts.templates.loader import PromptLoader
        from app.prompts.templates.renderer import PromptRenderer

        from app.agents.generator import CodeGenerationAgent

        agent = CodeGenerationAgent()
        loader = PromptLoader()
        renderer = PromptRenderer()
        template = loader.load(agent.file_prompt_id)
        assert template is not None, f"prompt not resolvable: {agent.file_prompt_id}"
        assert template.model_id, f"prompt has no model header: {agent.file_prompt_id}"
        expected_vars = {
            "definition",
            "service_plan_json",
            "source_boundary_json",
            "analysis_context_json",
            "regeneration_context_json",
            "file_path",
            "file_description",
            "shared_types_json",
        }
        assert expected_vars <= set(template.variables)
        variables = {name: "{}" for name in template.variables}
        rendered, err = renderer.render_safe(agent.file_prompt_id, variables)
        assert err == "", f"render failed for {agent.file_prompt_id}: {err!r}"
        assert "[MISSING:" not in rendered, f"unresolved variable in {agent.file_prompt_id}"

    def test_generator_declares_per_file_variables(self):
        from app.agents.generator import CodeGenerationAgent

        agent = CodeGenerationAgent()
        vars_ = agent._build_file_template_variables(
            service_plan={"id": "order-service"},
            source_boundary={"name": "OrderService"},
            analysis_data={},
            regeneration_context=None,
            file_path="src/main/java/com/emip/orderservice/OrderServiceApplication.java",
            file_description="Main application class",
            shared_types_json='{"base_package": "com.emip.orderservice", "types": []}',
        )
        assert vars_["file_path"].endswith("OrderServiceApplication.java")
        assert vars_["file_description"] == "Main application class"
        assert vars_["shared_types_json"].startswith('{"base_package": "com.emip.orderservice"')
        assert "service_plan_json" in vars_ and "definition" in vars_


class TestCodeGenerationAgentConsistencyGate:
    """Per-file generation must not produce cross-file name drift.

    Guards the observed failure: independently-generated files invented divergent
    class names (entity `Order` vs `OrderServiceEntity`, repository `OrderRepository`
    vs `OrderServiceRepository`, DTO `OrderDTO` vs `OrderServiceDto`), producing a
    project that cannot compile. Every file's intra-service imports must resolve to
    a type some generated file declares, otherwise the file falls back to the
    deterministic scaffold.
    """

    _PLAN = {
        "id": "order-service",
        "name": "OrderService",
        "package": "com.emip.orderservice",
        "broker_role": "kafka",
        "database": {"name": "order_db", "tables": ["orders"]},
        "server_port": 8081,
    }

    class _FakeEngine:
        def __init__(self, responder):
            self._responder = responder
            self._metadata = {"model_id": "fake-nova"}

        def invoke_ai_with_fallback(self, template_variables=None, **kwargs):
            path = (template_variables or {}).get("file_path", "")
            return self._responder(path), dict(self._metadata), True

    def _scaffold_controller_path(self, plan):
        base = plan["package"].replace(".", "/")
        return f"src/main/java/{base}/web/{'OrderService'}Controller.java"

    def _run(self, responder):
        from app.agents.generator import CodeGenerationAgent

        agent = CodeGenerationAgent(engine=self._FakeEngine(responder))
        code, metadata, used_ai = agent.run(
            service_plan=dict(self._PLAN),
            source_boundary={"name": "OrderService", "classes": ["OrderController"]},
            analysis_data={},
        )
        return code, metadata, used_ai

    def test_shared_types_manifest_declares_all_scaffold_types(self):
        from app.agents.generator import CodeGenerationAgent
        from app.codegen.project_builder import build_scaffold_service

        agent = CodeGenerationAgent()
        scaffold = build_scaffold_service(dict(self._PLAN))
        manifest = agent._build_shared_types_manifest(scaffold)
        names = {t["name"] for t in manifest["types"]}
        assert {"OrderServiceApplication", "OrderServiceController", "OrderServiceService",
                "OrderServiceRepository", "OrderServiceEntity", "OrderServiceDto",
                "OrderServiceKafkaEventListener"} <= names
        for t in manifest["types"]:
            assert t["package"].startswith("com.emip.orderservice")

    def test_file_importing_missing_type_falls_back_to_scaffold(self):
        controller_path = self._scaffold_controller_path(self._PLAN)

        def responder(path):
            if path == controller_path:
                return {
                    "path": path,
                    "content": (
                        "package com.emip.orderservice.web;\n"
                        "import com.emip.orderservice.dto.OrderDTO;\n"
                        "import com.emip.orderservice.service.OrderService;\n"
                        "public class OrderServiceController {}\n"
                    ),
                }
            return {"path": path, "content": f"package com.emip.orderservice;\n// AI content for {path}\n"}

        code, metadata, used_ai = self._run(responder)
        assert used_ai is True
        assert metadata["used_fallback"] is True
        # The broken controller was replaced by the scaffold version.
        controller = next(f for f in code["files"] if f["path"] == controller_path)
        assert "@RestController" in controller["content"]
        assert "OrderDTO" not in controller["content"]
        assert metadata["files_scaffold"] >= 1

    def test_diverent_names_entire_project_falls_back_to_scaffold(self):
        def responder(path):
            if path.endswith(".java"):
                return {
                    "path": path,
                    "content": (
                        "package com.emip.orderservice;\n"
                        "import com.emip.orderservice.entity.Order;\n"
                        "import com.emip.orderservice.repository.OrderRepository;\n"
                        "import com.emip.orderservice.dto.OrderDTO;\n"
                        "public class AnyService {}\n"
                    ),
                }
            if path.endswith("pom.xml"):
                return {"path": path, "content": "<project xmlns=\"http://maven.apache.org/POM/4.0.0\"></project>"}
            if path.endswith(".yml") or path.endswith(".yaml"):
                return {"path": path, "content": "server:\n  port: 8081\n"}
            if path.endswith("Dockerfile"):
                return {"path": path, "content": "FROM eclipse-temurin:17-jre\n"}
            return {"path": path, "content": "openapi: 3.0.0\n"}

        code, metadata, _ = self._run(responder)
        # Every Java file references missing types -> all fall back to the
        # deterministic scaffold; the assembled service is internally consistent.
        java_paths = [f["path"] for f in code["files"] if f["path"].endswith(".java")]
        assert len(java_paths) == 8
        assert metadata["files_scaffold"] == len(java_paths)
        assert metadata["files_ai"] == len(code["files"]) - len(java_paths)
        from app.agents.generator import CodeGenerationAgent

        assert CodeGenerationAgent._inconsistent_file_paths(code["files"], "com.emip.orderservice") == set()

    def test_inconsistent_file_paths_detects_drift(self):
        from app.agents.generator import CodeGenerationAgent

        files = [
            {"path": "A.java", "content": "package com.x;\npublic class A {}\n"},
            {"path": "B.java", "content": "package com.x.b;\nimport com.x.entity.Missing;\npublic class B {}\n"},
        ]
        bad = CodeGenerationAgent._inconsistent_file_paths(files, "com.x")
        assert bad == {"B.java"}

    def test_inconsistent_file_paths_ignores_resolved_imports(self):
        from app.agents.generator import CodeGenerationAgent

        files = [
            {"path": "A.java", "content": "package com.x;\npublic class OrderServiceEntity {}\n"},
            {"path": "B.java", "content": "package com.x.b;\nimport com.x.OrderServiceEntity;\npublic class B {}\n"},
        ]
        assert CodeGenerationAgent._inconsistent_file_paths(files, "com.x") == set()


class TestScaffoldCompiles:
    """P2.2 guards: generated code must be valid Java with consistent ports/paths."""

    def _build(self, **overrides):
        plan = {
            "id": "order-service",
            "package": "com.emip.orderservice",
            "server_port": 8081,
            "broker_role": "both",
            "events": {
                "publishes": [{"topic": "OrderCreated"}, {"topic": "Order-Cancelled"}],
                "subscribes": [{"queue": "order-email"}],
            },
            "feign_clients": [
                {"name": "inventory-client", "target_service": "inventory-service", "target_port": 8082},
            ],
        }
        plan.update(overrides)
        return build_scaffold_service(plan)

    def test_listener_method_names_are_valid_java(self):
        code = self._build()
        by_path = {f["path"]: f["content"] for f in code["files"]}
        kafka = by_path["src/main/java/com/emip/orderservice/messaging/OrderServiceKafkaEventListener.java"]
        rabbit = by_path["src/main/java/com/emip/orderservice/messaging/OrderServiceRabbitEventListener.java"]
        assert "onOrderCreated" in kafka
        assert "onOrderCancelled" in kafka
        assert "onOrderEmail" in rabbit
        assert "onorder" not in kafka and "onorder" not in rabbit

    def test_both_brokers_produce_distinct_listeners(self):
        code = self._build()
        paths = [f["path"] for f in code["files"]]
        assert any(p.endswith("KafkaEventListener.java") for p in paths)
        assert any(p.endswith("RabbitEventListener.java") for p in paths)
        assert len([p for p in paths if "messaging" in p]) == 2

    def test_feign_path_matches_controller_and_target_port(self):
        code = self._build(broker_role="none")
        by_path = {f["path"]: f["content"] for f in code["files"]}
        feign = by_path["src/main/java/com/emip/orderservice/client/InventoryClient.java"]
        controller = by_path["src/main/java/com/emip/orderservice/web/OrderServiceController.java"]
        controller_path = re.search(r'@RequestMapping\("([^"]+)"\)', controller).group(1)
        assert f'@GetMapping("{controller_path}")' in feign
        assert "/internal/" not in feign
        assert "http://inventory-service:8082" in feign
        assert "public interface InventoryClient" in feign

    def test_smoke_test_uses_h2_and_disables_brokers(self):
        code = self._build(broker_role="none")
        smoke = next(f["content"] for f in code["files"] if f["path"].endswith("SmokeTest.java"))
        assert "jdbc:h2:mem:testdb" in smoke
        assert "H2Dialect" in smoke
        assert "spring.kafka.listener.auto-startup=false" in smoke
        assert "spring.rabbitmq.listener.simple.auto-startup=false" in smoke
        assert "spring.rabbitmq.dynamic=false" in smoke

    def test_pom_includes_h2_test_dependency(self):
        code = self._build(broker_role="none")
        pom = next(f["content"] for f in code["files"] if f["path"].endswith("pom.xml"))
        assert "com.h2database" in pom
        assert "<scope>test</scope>" in pom

    def test_planner_assigns_unique_ports_and_removes_platform_wave(self):
        boundaries = [
            {"name": "OrderService", "business_capability": "Order", "classes": ["OrderController"]},
            {"name": "InventoryService", "business_capability": "Inventory", "classes": ["InventoryController"]},
        ]
        agent = ServicePlannerAgent()
        design = ArchitectureDesignerAgent().fallback_design(boundaries, {})
        plan = agent.fallback_plan(design, boundaries)
        services = codegen_models.normalize_service_list(plan)
        ports = [s["server_port"] for s in services]
        assert len(ports) == len(set(ports)) == len(boundaries)
        assert all(isinstance(p, int) and p >= 8081 for p in ports)
        wave_services = [sid for w in plan["waves"] for sid in w["services"]]
        assert not {"api-gateway", "config-server", "discovery"} & set(wave_services)

    def test_ordered_services_assigns_missing_ports_and_feign_targets(self):
        from app.codegen.orchestrator import CodeGenOrchestrator

        plan = {
            "waves": [{"wave": 0, "name": "Core", "services": ["svc-a", "svc-b"]}],
            "services": {
                "svc-a": {"id": "svc-a", "package": "com.emip.a",
                          "feign_clients": [{"name": "BClient", "target_service": "svc-b"}]},
                "svc-b": {"id": "svc-b", "package": "com.emip.b"},
            },
        }
        ordered = CodeGenOrchestrator()._ordered_services(plan)
        ports = [s["server_port"] for s in ordered]
        assert ports == [8081, 8082]
        svc_a = next(s for s in ordered if s["id"] == "svc-a")
        assert svc_a["feign_clients"][0]["target_port"] == 8082


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


class TestCodeGenerationAgentCompleteGuard:
    """CodeGenerationAgent must always assemble a complete service.

    Files are generated one Bedrock call at a time; each file falls back to the
    scaffold independently, so the assembled service is complete even when
    Bedrock truncates or returns garbage. Guards the "no Java sources
    generated" bug.
    """

    _PLAN = {
        "id": "order-service",
        "name": "OrderService",
        "package": "com.emip.orderservice",
        "broker_role": "none",
        "database": {"name": "order_db", "tables": ["orders"]},
        "server_port": 8081,
    }

    class _FakeEngine:
        def __init__(self, responder):
            self._responder = responder
            self._metadata = {"model_id": "fake-nova"}

        def invoke_ai_with_fallback(self, template_variables=None, **kwargs):
            path = (template_variables or {}).get("file_path", "")
            return self._responder(path), dict(self._metadata), True

    def _run(self, responder):
        from app.agents.generator import CodeGenerationAgent

        agent = CodeGenerationAgent(engine=self._FakeEngine(responder))
        code, metadata, used_ai = agent.run(
            service_plan=dict(self._PLAN),
            source_boundary={"name": "OrderService", "classes": ["OrderController"]},
            analysis_data={},
        )
        return code, metadata, used_ai

    @staticmethod
    def _responder_garbage(path):
        return {"raw_response": "truncated json"}

    @staticmethod
    def _responder_ai(path):
        return {"path": path, "content": f"AI content for {path}"}

    @staticmethod
    def _responder_empty(path):
        return {"path": path, "content": ""}

    @staticmethod
    def _responder_java_only_ai(path):
        if path.endswith(".java"):
            return {"path": path, "content": f"AI content for {path}"}
        return {"raw_response": "truncated json"}

    def test_is_complete_service(self):
        from app.agents.generator import CodeGenerationAgent

        complete = build_scaffold_service(dict(self._PLAN))
        assert CodeGenerationAgent._is_complete_service(complete) is True

        # Empty files
        assert CodeGenerationAgent._is_complete_service({"files": []}) is False

        # Only pom, no Java sources
        assert CodeGenerationAgent._is_complete_service(
            {"files": [{"path": "pom.xml", "content": "<x/>"}]}
        ) is False

        # Java without pom/config
        assert CodeGenerationAgent._is_complete_service(
            {"files": [{"path": "src/main/java/X.java", "content": "class X {}"}]}
        ) is False

        # Entity without repository is incomplete (mirrors the reviewer)
        assert CodeGenerationAgent._is_complete_service(
            {
                "files": [
                    {"path": "pom.xml", "content": "<x/>"},
                    {"path": "src/main/resources/application.yml", "content": "x"},
                    {"path": "src/main/java/com/emip/x/domain/OrderEntity.java", "content": "x"},
                ]
            }
        ) is False

    def test_all_fallbacks_still_produce_complete_service(self):
        code, metadata, used_ai = self._run(self._responder_garbage)
        paths = [f["path"] for f in code["files"]]
        assert any(p.endswith(".java") and p.startswith("src/main/java") for p in paths)
        assert any(p.endswith("pom.xml") for p in paths)
        assert metadata["files_scaffold"] == len(code["files"])
        assert metadata["files_ai"] == 0
        assert metadata["used_fallback"] is True
        assert used_ai is False

    def test_empty_content_uses_scaffold_for_that_file(self):
        code, metadata, _ = self._run(self._responder_empty)
        assert metadata["files_scaffold"] == len(code["files"])
        assert metadata["used_fallback"] is True

    def test_all_ai_files_no_fallback(self):
        code, metadata, used_ai = self._run(self._responder_ai)
        assert used_ai is True
        assert metadata["used_fallback"] is False
        assert metadata["files_ai"] == len(code["files"])
        for f in code["files"]:
            assert f["content"].startswith("AI content for")

    def test_mixed_ai_and_scaffold_reported(self):
        code, metadata, used_ai = self._run(self._responder_java_only_ai)
        assert used_ai is True
        assert metadata["used_fallback"] is True
        assert metadata["files_ai"] > 0
        assert metadata["files_scaffold"] > 0
        assert metadata["files_ai"] + metadata["files_scaffold"] == len(code["files"])
        assert any(
            p.endswith(".java") and p.startswith("src/main/java") for p in [f["path"] for f in code["files"]]
        )
