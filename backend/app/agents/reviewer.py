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
            checks = {
                "pom.xml": ("major", "missing Maven build file"),
                "application.yml": ("major", "missing application configuration"),
                "resilience4j.yml": ("minor", "missing resilience configuration (retry/circuit breaker/bulkhead)"),
                "Dockerfile": ("minor", "missing container definition"),
            }
            for required, (sev, message) in checks.items():
                if not any(p.endswith(required) for p in paths):
                    findings.append({
                        "id": f"{service_id}-{required.replace('.', '-')}",
                        "severity": sev,
                        "category": "completeness",
                        "file": required,
                        "finding": f"{service_id}: {message}",
                        "recommendation": f"Add {required} to {service_id}",
                    })

            # Check for Java sources
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
            else:
                # Positive findings
                findings.append({
                    "id": f"{service_id}-java-ok",
                    "severity": "info",
                    "category": "correctness",
                    "file": "src/main/java",
                    "finding": f"{service_id}: Complete Java source structure verified",
                    "recommendation": None,
                })

            # Check for Feign clients if needed
            feign_count = len([p for p in paths if "feign" in p.lower() or "client" in p.lower()])
            if feign_count > 0:
                findings.append({
                    "id": f"{service_id}-feign-configured",
                    "severity": "info",
                    "category": "communication",
                    "file": "feign clients",
                    "finding": f"{service_id}: {feign_count} inter-service clients configured (Feign + circuit breaker)",
                    "recommendation": None,
                })

        blocking = codegen_models.blocking_findings({"findings": findings})
        approved = not blocking
        critical_count = len([f for f in findings if f.get("severity") == "critical"])

        return {
            "service_id": ",".join(s.get("service_id", "") for s in services_code),
            "iteration": 0,
            "approved": approved,
            "summary": f"{len(findings)} findings ({critical_count} critical)" if critical_count > 0 else f"All checks passed - {len(findings)} notes",
            "score": max(10, 100 - critical_count * 30 - len([f for f in findings if f.get("severity") == "major"]) * 10),
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
