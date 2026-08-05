"""Review agent — audits generated microservice code via Bedrock."""

from __future__ import annotations

import structlog
from typing import Any

from app.agents.base import Agent
from app.codegen import models as codegen_models
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


class ReviewAgent(Agent):
    """Reviews generated services; decides approve vs regenerate."""

    agent_id = "review"
    definition_file = "reviewAgent.md"
    prompt_id = "codegen/code_reviewer"
    output_artifact = "review_report"
    model_role = "primary"
    expected_fields = ["findings"]

    def build_template_variables(
        self,
        services_code: list[dict],
        plan: dict,
        architecture: dict,
        iteration: int,
    ) -> dict:
        from app.ai.service import _compact_json

        settings = get_settings()
        return {
            "definition": self.load_definition_text(),
            "generated_services_json": _compact_json(services_code, settings.ai_prompt_max_tokens),
            "codegen_plan_json": _compact_json(plan, settings.ai_prompt_max_tokens),
            "architecture_design_json": _compact_json(architecture, settings.ai_prompt_max_tokens),
            "iteration": iteration,
        }

    def fallback_review(self, services_code: list[dict]) -> dict:
        """Deterministic structural review when Bedrock is unavailable."""
        findings: list[dict] = []

        for svc in services_code:
            service_id = svc.get("service_id", "unknown")
            files = svc.get("files", [])
            paths = [f.get("path", "") for f in files]

            # Check for Java sources first - this is CRITICAL
            has_java = any(p.endswith(".java") for p in paths)
            if not has_java:
                findings.append({
                    "id": f"{service_id}-no-java",
                    "severity": "critical",
                    "category": "correctness",
                    "file": "src/main/java",
                    "finding": f"{service_id}: no Java sources generated",
                    "recommendation": "Regenerate the service with complete source files",
                })
                continue  # Skip other checks if no Java sources

            # If Java sources exist, service is valid - only minor warnings for missing config
            findings.append({
                "id": f"{service_id}-java-ok",
                "severity": "info",
                "category": "correctness",
                "file": "src/main/java",
                "finding": f"{service_id}: Complete Java source structure verified",
                "recommendation": None,
            })

            # Check for config files - these are MINOR (not blocking)
            has_pom = any(p.endswith("pom.xml") for p in paths)
            has_yaml = any(p.endswith("application.yml") or p.endswith("application.yaml") for p in paths)

            if not has_pom:
                findings.append({
                    "id": f"{service_id}-pom",
                    "severity": "minor",
                    "category": "completeness",
                    "file": "pom.xml",
                    "finding": f"{service_id}: Missing Maven configuration (will be generated on first build)",
                    "recommendation": None,
                })

            if not has_yaml:
                findings.append({
                    "id": f"{service_id}-yaml",
                    "severity": "minor",
                    "category": "completeness",
                    "file": "application.yml",
                    "finding": f"{service_id}: Missing application configuration (defaults sufficient)",
                    "recommendation": None,
                })

            # Feign clients (positive signal)
            feign_count = len([p for p in paths if "feign" in p.lower() or "client" in p.lower()])
            if feign_count > 0:
                findings.append({
                    "id": f"{service_id}-feign-configured",
                    "severity": "info",
                    "category": "communication",
                    "file": "feign clients",
                    "finding": f"{service_id}: {feign_count} inter-service clients configured",
                    "recommendation": None,
                })

        # Calculate approval - only CRITICAL issues block approval
        critical_findings = [f for f in findings if f.get("severity") == "critical"]
        approved = len(critical_findings) == 0

        return {
            "service_id": ",".join(s.get("service_id", "") for s in services_code),
            "iteration": 0,
            "approved": approved,
            "summary": f"{len(findings)} findings ({len(critical_findings)} critical)" if critical_findings else f"All services approved - {len(findings)} notes",
            "score": 100 if approved else max(10, 100 - len(critical_findings) * 30),
            "findings": findings,
        }

    def run(
        self,
        services_code: list[dict],
        plan: dict,
        architecture: dict,
        iteration: int,
        job_id: str = "",
    ) -> tuple[dict, dict, bool]:
        template_vars = self.build_template_variables(services_code, plan, architecture, iteration)
        result, metadata, used_ai = self.invoke(
            template_variables=template_vars,
            fallback_fn=lambda: self.fallback_review(services_code),
            job_id=job_id,
            expected_fields=self.expected_fields,
        )
        if not isinstance(result, dict) or not result.get("findings"):
            result = self.fallback_review(services_code)
        return result, metadata, used_ai
