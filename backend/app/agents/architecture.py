"""Architecture Designer agent — designs the target microservice topology via Bedrock.

Produces the architecture_design artifact: service nodes, brokers (Kafka/RabbitMQ),
databases, the API gateway, typed edges, and a resilience matrix. This is the
Bedrock-generated graph the Architecture page renders.
"""

from __future__ import annotations

import structlog
from typing import Any

from app.agents.base import Agent
from app.codegen import models as codegen_models
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


class ArchitectureDesignerAgent(Agent):
    """Designs the target architecture and messaging topology."""

    agent_id = "architecture_designer"
    definition_file = "architectureDesignerAgent.md"
    prompt_id = "codegen/architecture_designer"
    output_artifact = "architecture_design"
    model_role = "primary"
    expected_fields = ["nodes", "edges"]

    def build_template_variables(
        self, analysis_data: dict, boundaries: list[dict], waves: dict, cost: dict
    ) -> dict:
        """Assemble prompt variables from analysis artifacts."""
        from app.ai.service import _compact_json

        settings = get_settings()
        return {
            "definition": self.load_definition_text(),
            "static_analysis_json": _compact_json(analysis_data, settings.ai_prompt_max_tokens),
            "boundaries_json": _compact_json(boundaries, settings.ai_prompt_max_tokens),
            "migration_waves_json": _compact_json(waves, settings.ai_prompt_max_tokens),
            "cost_analysis_json": _compact_json(cost, settings.ai_prompt_max_tokens),
        }

    def fallback_design(self, boundaries: list[dict], analysis_data: dict) -> dict:
        """Deterministic architecture when Bedrock is unavailable."""
        from app.ai.service import _compact_json

        nodes = [{"id": "api-gateway", "type": "gateway", "label": "API Gateway", "subtype": "spring-cloud-gateway"}]
        edges: list[dict] = []
        services: list[dict] = []
        brokers: list[dict] = []
        topics: list[dict] = []
        queues: list[dict] = []

        dependency_index: dict[str, list[str]] = {}
        if analysis_data:
            for edge in analysis_data.get("dependency_edges", []):
                src = edge.get("source") if isinstance(edge, dict) else None
                dst = edge.get("target") if isinstance(edge, dict) else None
                if src and dst:
                    dependency_index.setdefault(src, []).append(dst)

        service_ids: list[str] = []
        for i, svc in enumerate(boundaries):
            svc_id = codegen_models.normalize_service_id(svc, f"service-{i}")
            service_ids.append(svc_id)

            # Classify broker role based on dependencies
            broker_role = "none"
            broker_rationale = "synchronous REST calls only"
            coupled_services = dependency_index.get(svc.get("name", ""), [])
            if len(coupled_services) > 2:
                broker_role = "rabbitmq"
                broker_rationale = "High coupling detected; command queue pattern for orchestration"
            elif len(coupled_services) > 0:
                broker_role = "kafka"
                broker_rationale = "Inter-service events and data propagation"

            services.append({
                "id": svc_id,
                "name": svc.get("name", svc_id),
                "business_capability": svc.get("business_capability", ""),
                "source_boundary": svc.get("name", svc_id),
                "tech_stack": ["spring-boot-3", "spring-data-jpa", "openfeign"],
                "broker_role": broker_role,
                "broker_rationale": broker_rationale,
                "resilience": ["retry", "circuit-breaker", "time-limiter", "bulkhead"],
                "database": {"engine": "postgresql", "name": f"{svc_id}_db"},
                "exposed_endpoints": [{"method": "GET", "path": f"/api/{svc_id}"}],
                "feign_clients": [{"target_service": sid} for sid in coupled_services[:3]],
            })
            nodes.append({"id": svc_id, "type": "service", "label": svc.get("name", svc_id), "broker_role": broker_role})
            nodes.append({"id": f"{svc_id}-db", "type": "database", "label": f"{svc_id}_db"})
            edges.append({
                "id": f"gateway-{svc_id}",
                "source": "api-gateway",
                "target": svc_id,
                "type": "rest",
                "label": f"/api/{svc_id}",
            })
            edges.append({
                "id": f"{svc_id}-db",
                "source": svc_id,
                "target": f"{svc_id}-db",
                "type": "database",
                "label": "JPA",
            })

        # Add inter-service Feign edges
        for i, svc_id in enumerate(service_ids):
            svc = boundaries[i] if i < len(boundaries) else {}
            coupled = dependency_index.get(svc.get("name", ""), [])
            for target in coupled[:3]:
                edges.append({
                    "id": f"{svc_id}-{target}",
                    "source": svc_id,
                    "target": target,
                    "type": "feign",
                    "label": "Feign client",
                })

        if not brokers:
            pass

        return {
            "version": "1.0.0",
            "services": services,
            "nodes": nodes,
            "edges": edges,
            "message_topology": {"topics": [], "queues": []},
            "fallback": True,
        }

    def run(
        self,
        analysis_data: dict,
        boundaries: list[dict],
        waves: dict,
        cost: dict,
        job_id: str = "",
    ) -> tuple[dict, dict, bool]:
        """Invoke Bedrock to design the architecture; falls back deterministically."""
        template_vars = self.build_template_variables(analysis_data, boundaries, waves, cost)
        result, metadata, used_ai = self.invoke(
            template_variables=template_vars,
            fallback_fn=lambda: self.fallback_design(boundaries, analysis_data),
            job_id=job_id,
            expected_fields=self.expected_fields,
        )
        if isinstance(result, dict):
            result = codegen_models.normalize_architecture(result)
        else:
            result = self.fallback_design(boundaries, analysis_data)
        return result, metadata, used_ai
