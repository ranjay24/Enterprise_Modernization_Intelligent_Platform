"""Service Planner agent — orders services into build waves and defines contracts."""

from __future__ import annotations

import structlog
from typing import Any

from app.agents.base import Agent
from app.codegen import models as codegen_models
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


class ServicePlannerAgent(Agent):
    """Produces the codegen_plan: build waves + per-service build scope."""

    agent_id = "service_planner"
    definition_file = "servicePlannerAgent.md"
    prompt_id = "codegen/service_planner"
    output_artifact = "codegen_plan"
    model_role = "primary"
    expected_fields = ["waves"]

    def build_template_variables(
        self,
        architecture: dict,
        boundaries: list[dict],
        analysis_data: dict,
        review_feedback: list[dict] | None = None,
    ) -> dict:
        from app.ai.service import _compact_json

        settings = get_settings()
        return {
            "definition": self.load_definition_text(),
            "architecture_design_json": _compact_json(architecture, settings.ai_prompt_max_tokens),
            "boundaries_json": _compact_json(boundaries, settings.ai_prompt_max_tokens),
            "analysis_data_json": _compact_json(analysis_data, settings.ai_prompt_max_tokens),
            "review_feedback_json": _compact_json(review_feedback or [], settings.ai_prompt_max_tokens),
        }

    def fallback_plan(self, architecture: dict, boundaries: list[dict]) -> dict:
        """Deterministic wave plan derived from the architecture's services."""
        services = architecture.get("services") or []
        svc_ids = [codegen_models.normalize_service_id(s) for s in services if codegen_models.normalize_service_id(s)]
        edges = architecture.get("edges", [])

        # Build Feign client index from edges
        feign_clients_by_source: dict[str, list[str]] = {}
        for edge in edges:
            if edge.get("type") == "feign":
                source = edge.get("source", "")
                target = edge.get("target", "")
                if source and target:
                    feign_clients_by_source.setdefault(source, []).append(target)

        # Unique port per service; 8080 is reserved for the API gateway (deployment-level).
        ports = {sid: 8081 + i for i, sid in enumerate(svc_ids)}
        waves: list[dict] = []
        service_plans: dict[str, dict] = {}
        for svc in services:
            svc_id = codegen_models.normalize_service_id(svc)
            if not svc_id:
                continue

            # Get Feign clients for this service
            feign_targets = feign_clients_by_source.get(svc_id, [])
            feign_list = [{"name": f"{t}Client", "target_service": t, "target_port": ports.get(t, 8081)} for t in feign_targets]

            service_plans[svc_id] = {
                "id": svc_id,
                "package": f"com.emip.{svc_id.lower().replace('-', '')}",
                "source_boundary": svc.get("source_boundary", svc.get("name", svc_id)),
                "source_classes": [],
                "server_port": ports.get(svc_id, 8081),
                "exposed_endpoints": svc.get("exposed_endpoints", []),
                "internal_endpoints": [],
                "feign_clients": feign_list,
                "events": svc.get("events", {"publishes": [], "subscribes": []}),
                "broker_role": codegen_models.broker_role_of(svc),
                "broker_rationale": svc.get("broker_rationale", ""),
                "resilience": {
                    "retry": {"max_attempts": 3, "backoff_ms": 500},
                    "circuit_breaker": {"failure_rate_threshold": 50, "wait_duration_seconds": 10},
                    "rate_limiter": {"limit_for_period": 100, "limit_refresh_period_seconds": 1},
                    "time_limiter": {"timeout_duration_seconds": 3},
                    "bulkhead": {"max_concurrent_calls": 20},
                },
                "database": svc.get("database", {"engine": "postgresql", "name": f"{svc_id}_db", "tables": []}),
            }

        if svc_ids:
            waves.append({"wave": 0, "name": "Core Business", "services": svc_ids, "rationale": "business services"})

        return {
            "version": "1.0.0",
            "waves": waves,
            "services": service_plans,
            "global_config": {
                "base_package": "com.emip",
                "java_version": "17",
                "spring_boot_version": "3.3.4",
                "maven_group_id": "com.emip",
            },
            "fallback": True,
        }

    def run(
        self,
        architecture: dict,
        boundaries: list[dict],
        analysis_data: dict,
        review_feedback: list[dict] | None = None,
        job_id: str = "",
    ) -> tuple[dict, dict, bool]:
        template_vars = self.build_template_variables(
            architecture, boundaries, analysis_data, review_feedback
        )
        result, metadata, used_ai = self.invoke(
            template_variables=template_vars,
            fallback_fn=lambda: self.fallback_plan(architecture, boundaries),
            job_id=job_id,
            expected_fields=self.expected_fields,
        )
        if not isinstance(result, dict) or not result.get("waves"):
            result = self.fallback_plan(architecture, boundaries)
        return result, metadata, used_ai
